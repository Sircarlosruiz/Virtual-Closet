from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.generacion import GeneracionCreate, GeneracionResponse
from core.celery_app import app as celery_app
from core.database import get_db
from core.dependencies import get_current_mayorista
from models.mayorista import Mayorista
from repositories.generacion_repo import GeneracionRepository
from repositories.modelo_ia_repo import ModeloIARepository
from repositories.prenda_repo import PrendaRepository
from services.generacion_service import GeneracionService
from services.storage_service import StorageService

router = APIRouter(tags=["generaciones"])


def _get_generacion_service(db: AsyncSession = Depends(get_db)) -> GeneracionService:
    return GeneracionService(
        generacion_repo=GeneracionRepository(db),
        modelo_ia_repo=ModeloIARepository(db),
        prenda_repo=PrendaRepository(db),
        storage=StorageService(),
    )


@router.post("/api/generaciones", response_model=GeneracionResponse, status_code=201)
async def crear_generacion(
    body: GeneracionCreate,
    mayorista: Mayorista = Depends(get_current_mayorista),
    service: GeneracionService = Depends(_get_generacion_service),
):
    generacion = await service.crear_generacion(
        mayorista_id=mayorista.id,
        prenda_id=body.prenda_id,
        modelo_ia_id=body.modelo_ia_id,
        plan=mayorista.plan,
    )

    queue = "vton.generation.priority" if mayorista.plan == "pro" else "vton.generation.normal"
    celery_app.send_task(
        "tasks.generate_vton",
        args=[str(generacion.id)],
        queue=queue,
    )

    presigned = await service.get_presigned_urls(generacion)
    return GeneracionResponse(
        id=generacion.id,
        prenda_id=generacion.prenda_id,
        modelo_ia_id=generacion.modelo_ia_id,
        estado=generacion.estado,
        imagen_url=presigned.get("imagen_url"),
        thumbnail_url=presigned.get("thumbnail_url"),
        costo_inferencia_usd=float(generacion.costo_inferencia_usd) if generacion.costo_inferencia_usd else None,
        error_message=generacion.error_message,
        created_at=generacion.created_at.isoformat(),
    )


@router.get("/api/generaciones/{generacion_id}", response_model=GeneracionResponse)
async def get_generacion(
    generacion_id: str,
    mayorista: Mayorista = Depends(get_current_mayorista),
    service: GeneracionService = Depends(_get_generacion_service),
):
    from uuid import UUID
    generacion = await service.get_generacion(UUID(generacion_id), mayorista.id)
    presigned = await service.get_presigned_urls(generacion)
    return GeneracionResponse(
        id=generacion.id,
        prenda_id=generacion.prenda_id,
        modelo_ia_id=generacion.modelo_ia_id,
        estado=generacion.estado,
        imagen_url=presigned.get("imagen_url"),
        thumbnail_url=presigned.get("thumbnail_url"),
        costo_inferencia_usd=float(generacion.costo_inferencia_usd) if generacion.costo_inferencia_usd else None,
        error_message=generacion.error_message,
        created_at=generacion.created_at.isoformat(),
    )


@router.get("/api/prendas/{prenda_id}/generaciones", response_model=list[GeneracionResponse])
async def list_generaciones_prenda(
    prenda_id: str,
    mayorista: Mayorista = Depends(get_current_mayorista),
    service: GeneracionService = Depends(_get_generacion_service),
):
    from uuid import UUID
    generaciones = await service.get_generaciones_by_prenda(UUID(prenda_id), mayorista.id)
    result = []
    for g in generaciones:
        presigned = await service.get_presigned_urls(g)
        result.append(GeneracionResponse(
            id=g.id,
            prenda_id=g.prenda_id,
            modelo_ia_id=g.modelo_ia_id,
            estado=g.estado,
            imagen_url=presigned.get("imagen_url"),
            thumbnail_url=presigned.get("thumbnail_url"),
            costo_inferencia_usd=float(g.costo_inferencia_usd) if g.costo_inferencia_usd else None,
            error_message=g.error_message,
            created_at=g.created_at.isoformat(),
        ))
    return result
