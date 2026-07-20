import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.batches import (
    BatchCreateRequest,
    BatchCreateResponse,
    BatchDetailResponse,
    BatchItemResponse,
    BatchListItemResponse,
    BatchListResponse,
)
from core.dependencies import get_current_mayorista, get_db
from repositories.batch_repo import BatchJobRepo
from repositories.media_repo import GarmentPhotoRepo, ModelPhotoRepo
from repositories.vton_job_repo import VTONJobRepo
from services.batch_submission_service import (
    BatchSizeExceededError,
    BatchSubmissionError,
    BatchSubmissionService,
    EmptyBatchError,
    MayoristaOwnershipError,
)
from services.batch_retry_service import (
    BatchRetryService,
    ItemNotFailedError,
    RetryEnqueueError,
)
from services.vton_job_service import VTONJobService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/batches", tags=["batches"])


def _get_batch_submission_service(
    db: AsyncSession = Depends(get_db),
) -> BatchSubmissionService:
    """Dependency injector for BatchSubmissionService."""
    batch_repo = BatchJobRepo(db)
    garment_repo = GarmentPhotoRepo(db)
    model_repo = ModelPhotoRepo(db)
    vton_job_repo = VTONJobRepo(db)
    vton_service = VTONJobService(
        vton_job_repo=vton_job_repo,
        garment_repo=garment_repo,
        model_repo=model_repo,
        minio_client=None,  # Not needed for batch submission
    )
    return BatchSubmissionService(
        batch_repo=batch_repo,
        garment_repo=garment_repo,
        model_repo=model_repo,
        vton_job_service=vton_service,
    )


@router.post("", status_code=201)
async def create_batch(
    request: BatchCreateRequest,
    mayorista=Depends(get_current_mayorista),
    service: BatchSubmissionService = Depends(_get_batch_submission_service),
    db: AsyncSession = Depends(get_db),
) -> BatchCreateResponse:
    """Submit a new batch of VTON pairings.

    Creates a BatchJob with all items and enqueues VTON jobs atomically.
    """
    try:
        batch = await service.create_and_submit(
            mayorista_id=mayorista.id,
            request=request,
            db=db,
            tenant_id=mayorista.tenant_id,
        )
        await db.commit()
        service.publish_pending()
    except EmptyBatchError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "EMPTY_BATCH",
                "message": str(exc),
            },
        )
    except BatchSizeExceededError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "BATCH_SIZE_EXCEEDED",
                "message": str(exc),
            },
        )
    except MayoristaOwnershipError as exc:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "OWNERSHIP_VIOLATION",
                "message": str(exc),
            },
        )
    except BatchSubmissionError as exc:
        await db.rollback()
        logger.error("Batch submission failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail={
                "code": "SUBMISSION_FAILED",
                "message": "Batch submission failed, no records created",
                "context": {"reason": str(exc)},
            },
        )

    return BatchCreateResponse(
        id=batch.id,
        name=batch.name,
        status=batch.status,
        total_items=batch.total_items,
        completed_count=batch.completed_count,
        failed_count=batch.failed_count,
        created_at=batch.created_at,
    )


@router.get("/{batch_id}")
async def get_batch(
    batch_id: uuid.UUID,
    mayorista=Depends(get_current_mayorista),
    db: AsyncSession = Depends(get_db),
) -> BatchDetailResponse:
    """Get batch details including all items."""
    repo = BatchJobRepo(db)
    batch = await repo.get_by_id_and_mayorista(batch_id, mayorista.id)
    if batch is None:
        exists = await repo.get_by_id(batch_id)
        if exists is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "BATCH_NOT_FOUND",
                    "message": "Batch not found",
                },
            )
        raise HTTPException(
            status_code=403,
            detail={
                "code": "OWNERSHIP_VIOLATION",
                "message": "You do not own this batch",
            },
        )

    return BatchDetailResponse(
        id=batch.id,
        name=batch.name,
        status=batch.status,
        total_items=batch.total_items,
        completed_count=batch.completed_count,
        failed_count=batch.failed_count,
        created_at=batch.created_at,
        completed_at=batch.completed_at,
        items=[
            BatchItemResponse(
                id=item.id,
                garment_id=item.garment_id,
                model_id=item.model_id,
                cloth_type=item.cloth_type,
                status=item.status,
                vton_job_id=item.vton_job_id,
                error_message=item.error_message,
                retry_count=item.retry_count,
                created_at=item.created_at,
            )
            for item in batch.items
        ],
    )


@router.get("")
async def list_batches(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    mayorista=Depends(get_current_mayorista),
    db: AsyncSession = Depends(get_db),
) -> BatchListResponse:
    """List mayorista's batches with pagination."""
    repo = BatchJobRepo(db)
    batches, total = await repo.list_by_mayorista(
        mayorista.id, page, page_size
    )

    return BatchListResponse(
        items=[
            BatchListItemResponse(
                id=b.id,
                name=b.name,
                status=b.status,
                total_items=b.total_items,
                completed_count=b.completed_count,
                failed_count=b.failed_count,
                created_at=b.created_at,
            )
            for b in batches
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/{batch_id}/items/{item_id}/retry")
async def retry_item(
    batch_id: uuid.UUID,
    item_id: uuid.UUID,
    mayorista=Depends(get_current_mayorista),
    db: AsyncSession = Depends(get_db),
) -> BatchItemResponse:
    """Retry a failed batch item.

    Creates a new VtonJob for the same pairing and resets the item status.
    """
    batch_repo = BatchJobRepo(db)
    garment_repo = GarmentPhotoRepo(db)
    model_repo = ModelPhotoRepo(db)
    vton_job_repo = VTONJobRepo(db)
    vton_service = VTONJobService(
        vton_job_repo=vton_job_repo,
        garment_repo=garment_repo,
        model_repo=model_repo,
        minio_client=None,
    )
    retry_service = BatchRetryService(
        batch_repo=batch_repo,
        vton_job_service=vton_service,
        db=db,
    )

    try:
        item = await retry_service.retry_item(
            batch_id=batch_id,
            item_id=item_id,
            mayorista_id=mayorista.id,
        )
        await db.commit()
    except MayoristaOwnershipError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=403,
            detail={
                "code": "OWNERSHIP_VIOLATION",
                "message": str(exc),
            },
        )
    except ItemNotFailedError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail={
                "code": "ITEM_NOT_FAILED",
                "message": str(exc),
            },
        )
    except RetryEnqueueError as exc:
        await db.rollback()
        logger.error("Retry enqueue failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail={
                "code": "RETRY_FAILED",
                "message": "Failed to enqueue retry",
                "context": {"reason": str(exc)},
            },
        )

    return BatchItemResponse(
        id=item.id,
        garment_id=item.garment_id,
        model_id=item.model_id,
        cloth_type=item.cloth_type,
        status=item.status,
        vton_job_id=item.vton_job_id,
        error_message=item.error_message,
        retry_count=item.retry_count,
        created_at=item.created_at,
    )
