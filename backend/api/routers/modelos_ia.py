from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.modelo_ia import ModeloIAResponse
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
    modelos = await service.get_by_plan(mayorista.plan)
    return modelos
