from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.modelo_ia import ModeloIACreateRequest, ModeloIAResponse
from core.database import get_db
from core.dependencies import get_current_mayorista
from models.mayorista import Mayorista
from repositories.modelo_ia_repo import ModeloIARepository
from services.modelo_ia_service import ModeloIAService
from services.storage_service import StorageService

router = APIRouter(tags=["modelos-ia"])


def _get_modelo_ia_service(db: AsyncSession = Depends(get_db)) -> ModeloIAService:
    return ModeloIAService(
        repo=ModeloIARepository(db),
        storage=StorageService(),
    )


@router.get("/api/modelos-ia", response_model=list[ModeloIAResponse])
async def list_modelos_ia(
    mayorista: Mayorista = Depends(get_current_mayorista),
    service: ModeloIAService = Depends(_get_modelo_ia_service),
):
    modelos = await service.get_by_plan(mayorista.plan, mayorista.id)
    return modelos


@router.get("/api/modelos-ia/upload-url")
async def get_modelo_upload_url(
    extension: str = "jpg",
    mayorista: Mayorista = Depends(get_current_mayorista),
    service: ModeloIAService = Depends(_get_modelo_ia_service),
):
    if extension not in ("jpg", "jpeg", "png"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato no soportado. Usa jpg o png.",
        )
    modelo_id, upload_url, object_key = await service.generate_upload_url(extension)
    return {
        "upload_url": upload_url,
        "modelo_id": modelo_id,
        "object_key": object_key,
    }


@router.post("/api/modelos-ia", response_model=ModeloIAResponse, status_code=status.HTTP_201_CREATED)
async def crear_modelo(
    data: ModeloIACreateRequest,
    mayorista: Mayorista = Depends(get_current_mayorista),
    service: ModeloIAService = Depends(_get_modelo_ia_service),
):
    try:
        modelo = await service.create_modelo(
            mayorista_id=mayorista.id,
            modelo_id=data.modelo_id,
            nombre=data.nombre,
            descripcion=data.descripcion,
            object_key=data.object_key,
        )
        return modelo
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error al crear el modelo",
        )
