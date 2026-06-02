from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from api.schemas.media import (
    ExtractedGarmentResponse,
    GarmentPhotoResponse,
    ModelPhotoResponse,
    PaginatedExtractedGarments,
    PaginatedGarmentPhotos,
    PaginatedModelPhotos,
)
from core.database import get_db
from core.dependencies import get_current_mayorista
from core.minio_client import MinIOClient
from models.mayorista import Mayorista
from repositories.media_repo import GarmentPhotoRepo, MediaItemRepo, ModelPhotoRepo
from services.media_library_service import MediaLibraryService
from services.media_service import (
    EmptyFileError,
    FileTooLargeError,
    InvalidFileTypeError,
    MediaUploadService,
)
from services.model_library_service import ModelLibraryService

router = APIRouter(prefix="/api/media", tags=["media"])


def _get_upload_service(db: AsyncSession = Depends(get_db)) -> MediaUploadService:
    garment_repo = GarmentPhotoRepo(db)
    model_repo = ModelPhotoRepo(db)
    minio_client = MinIOClient()
    return MediaUploadService(garment_repo, model_repo, minio_client)


def _get_library_service(db: AsyncSession = Depends(get_db)) -> ModelLibraryService:
    model_repo = ModelPhotoRepo(db)
    minio_client = MinIOClient()
    return ModelLibraryService(model_repo, minio_client)


def _get_media_library_service(db: AsyncSession = Depends(get_db)) -> MediaLibraryService:
    media_item_repo = MediaItemRepo(db)
    minio_client = MinIOClient()
    return MediaLibraryService(media_item_repo, minio_client)


# --- Garment Photo Upload ---


@router.post(
    "/garments",
    response_model=GarmentPhotoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_garment_photo(
    file: UploadFile = File(...),
    mayorista: Mayorista = Depends(get_current_mayorista),
    upload_service: MediaUploadService = Depends(_get_upload_service),
):
    """Upload a garment photo (JPG/PNG, max 10MB)."""
    file_bytes = await file.read()

    try:
        garment_photo, presigned_url = await upload_service.upload_garment(
            mayorista_id=mayorista.id,
            file_bytes=file_bytes,
            filename=file.filename or "unknown",
            content_type=file.content_type,
        )
    except EmptyFileError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except InvalidFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return GarmentPhotoResponse(
        id=garment_photo.id,
        presigned_url=presigned_url,
        filename=garment_photo.filename,
        uploaded_at=garment_photo.uploaded_at,
    )


@router.get("/garments", response_model=PaginatedGarmentPhotos)
async def list_garment_photos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    mayorista: Mayorista = Depends(get_current_mayorista),
    upload_service: MediaUploadService = Depends(_get_upload_service),
    library_service: ModelLibraryService = Depends(_get_library_service),
):
    """List mayorista's uploaded garment photos with presigned URLs."""
    items, total = await upload_service._garment_repo.list_by_mayorista(
        mayorista.id, page, page_size
    )
    garment_responses = []
    for garment in items:
        presigned_url = await library_service.get_presigned_url(garment.minio_key)
        garment_responses.append(
            GarmentPhotoResponse(
                id=garment.id,
                presigned_url=presigned_url,
                filename=garment.filename,
                uploaded_at=garment.uploaded_at,
            )
        )
    return PaginatedGarmentPhotos(
        items=garment_responses, total=total, page=page, page_size=page_size
    )


# --- Model Photo Upload ---


@router.post(
    "/models",
    response_model=ModelPhotoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_model_photo(
    file: UploadFile = File(...),
    label: str | None = None,
    mayorista: Mayorista = Depends(get_current_mayorista),
    upload_service: MediaUploadService = Depends(_get_upload_service),
):
    """Upload a model photo (JPG/PNG, max 10MB)."""
    file_bytes = await file.read()

    try:
        model_photo, presigned_url = await upload_service.upload_model_photo(
            mayorista_id=mayorista.id,
            file_bytes=file_bytes,
            filename=file.filename or "unknown",
            content_type=file.content_type,
            label=label,
        )
    except EmptyFileError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except InvalidFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return ModelPhotoResponse(
        id=model_photo.id,
        presigned_url=presigned_url,
        label=model_photo.label,
        is_curated=model_photo.is_curated,
        uploaded_at=model_photo.uploaded_at,
    )


@router.get("/models/mine", response_model=PaginatedModelPhotos)
async def list_own_model_photos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    mayorista: Mayorista = Depends(get_current_mayorista),
    library_service: ModelLibraryService = Depends(_get_library_service),
):
    """List mayorista's own uploaded model photos."""
    items, total = await library_service.list_own_models(
        mayorista.id, page, page_size
    )
    model_responses = []
    for model, presigned_url in items:
        model_responses.append(
            ModelPhotoResponse(
                id=model.id,
                presigned_url=presigned_url,
                label=model.label,
                is_curated=model.is_curated,
                uploaded_at=model.uploaded_at,
            )
        )
    return PaginatedModelPhotos(
        items=model_responses, total=total, page=page, page_size=page_size
    )


@router.get("/models/curated", response_model=list[ModelPhotoResponse])
async def list_curated_models(
    library_service: ModelLibraryService = Depends(_get_library_service),
    mayorista: Mayorista = Depends(get_current_mayorista),
):
    """List the curated model library (read-only, available to all mayoristas)."""
    items = await library_service.list_curated_models()
    return [
        ModelPhotoResponse(
            id=model.id,
            presigned_url=presigned_url,
            label=model.label,
            is_curated=model.is_curated,
            uploaded_at=model.uploaded_at,
        )
        for model, presigned_url in items
    ]


# --- Extracted Garments ---


@router.get("/extracted-garments", response_model=PaginatedExtractedGarments)
async def list_extracted_garments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    mayorista: Mayorista = Depends(get_current_mayorista),
    library_service: MediaLibraryService = Depends(_get_media_library_service),
):
    """List extracted garments for the authenticated mayorista."""
    items, total = await library_service.list_extracted_garments(
        mayorista.id, page, page_size
    )
    garment_responses = []
    for item in items:
        presigned_url = await library_service.get_presigned_url(item.minio_key)
        metadata = item.item_metadata or {}
        garment_responses.append(
            ExtractedGarmentResponse(
                id=item.id,
                presigned_url=presigned_url,
                filename=item.filename,
                garment_type=metadata.get("garment_type", "unknown"),
                source_image_id=uuid.UUID(metadata["source_image_id"]),
                source_job_id=uuid.UUID(metadata["source_job_id"]),
                created_at=item.created_at,
            )
        )
    return PaginatedExtractedGarments(
        items=garment_responses, total=total, page=page, page_size=page_size
    )


@router.get("/extracted-garments/{garment_id}", response_model=ExtractedGarmentResponse)
async def get_extracted_garment(
    garment_id: UUID,
    mayorista: Mayorista = Depends(get_current_mayorista),
    library_service: MediaLibraryService = Depends(_get_media_library_service),
):
    """Get a single extracted garment by ID."""
    item = await library_service.get_garment_by_id(garment_id, mayorista.id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Garment not found"
        )
    presigned_url = await library_service.get_presigned_url(item.minio_key)
    metadata = item.item_metadata or {}
    return ExtractedGarmentResponse(
        id=item.id,
        presigned_url=presigned_url,
        filename=item.filename,
        garment_type=metadata.get("garment_type", "unknown"),
        source_image_id=uuid.UUID(metadata["source_image_id"]),
        source_job_id=uuid.UUID(metadata["source_job_id"]),
        created_at=item.created_at,
    )
