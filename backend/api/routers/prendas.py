from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from api.schemas.prenda import (
    ActualizarNombreRequest,
    ConfirmarSubidaRequest,
    PrendaResponse,
    PrendasListResponse,
    UploadUrlRequest,
    UploadUrlResponse,
)
from core.database import get_db
from core.dependencies import get_current_mayorista
from models.mayorista import Mayorista
from repositories.prenda_repo import PrendaRepository
from services.prenda_service import (
    FormatoImagenNoSoportadoError,
    LimiteMensualAlcanzadoError,
    PrendaNoEncontradaError,
    PrendaService,
)
from services.storage_service import StorageService

router = APIRouter(prefix="/api/prendas", tags=["prendas"])


def _get_prenda_service(db: AsyncSession = Depends(get_db)) -> PrendaService:
    repo = PrendaRepository(db)
    storage = StorageService()
    return PrendaService(repo, storage)


@router.post("/upload", response_model=PrendaResponse, status_code=status.HTTP_201_CREATED)
async def subir_prenda(
    file: UploadFile = File(...),
    nombre: str = Form(""),
    mayorista: Mayorista = Depends(get_current_mayorista),
    prenda_service: PrendaService = Depends(_get_prenda_service),
):
    try:
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El archivo está vacío",
            )
        return await prenda_service.subir_prenda(
            mayorista.id,
            file_bytes,
            file.filename,
            file.content_type,
            nombre,
        )
    except LimiteMensualAlcanzadoError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Límite mensual alcanzado",
        )
    except FormatoImagenNoSoportadoError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato no soportado. Usa JPG, PNG o HEIC.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al subir la prenda: {exc}",
        ) from exc


@router.get("/upload-url", response_model=UploadUrlResponse)
async def get_upload_url(
    extension: str = Query(..., pattern="^(jpg|jpeg|png|heic)$"),
    mayorista: Mayorista = Depends(get_current_mayorista),
    prenda_service: PrendaService = Depends(_get_prenda_service),
):
    ext = "jpg" if extension == "jpeg" else extension
    try:
        result = await prenda_service.iniciar_subida(mayorista.id, ext)
        return result
    except LimiteMensualAlcanzadoError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Límite mensual alcanzado",
        )


@router.post("", response_model=PrendaResponse, status_code=status.HTTP_201_CREATED)
async def confirmar_subida(
    body: ConfirmarSubidaRequest,
    mayorista: Mayorista = Depends(get_current_mayorista),
    prenda_service: PrendaService = Depends(_get_prenda_service),
):
    try:
        prenda = await prenda_service.confirmar_subida(
            mayorista.id, body.prenda_id, body.nombre or "", body.object_key
        )
        return prenda
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        detail = "Error al confirmar la subida"
        if "imagen_original_key" in str(exc):
            detail = (
                "Falta aplicar migraciones de base de datos. "
                "Ejecuta: make db-migrate"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        ) from exc


@router.get("", response_model=PrendasListResponse)
async def list_prendas(
    cursor: UUID | None = Query(None),
    limit: int = Query(20, le=50),
    mayorista: Mayorista = Depends(get_current_mayorista),
    prenda_service: PrendaService = Depends(_get_prenda_service),
):
    prendas = await prenda_service.listar(mayorista.id, cursor)
    next_cursor = prendas[-1].id if len(prendas) == limit else None
    return PrendasListResponse(items=prendas, next_cursor=next_cursor)


@router.patch("/{prenda_id}", response_model=PrendaResponse)
async def update_nombre(
    prenda_id: UUID,
    body: ActualizarNombreRequest,
    mayorista: Mayorista = Depends(get_current_mayorista),
    prenda_service: PrendaService = Depends(_get_prenda_service),
):
    try:
        prenda = await prenda_service.actualizar_nombre(
            prenda_id, mayorista.id, body.nombre
        )
        return prenda
    except PrendaNoEncontradaError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prenda no encontrada",
        )


@router.delete("/{prenda_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prenda(
    prenda_id: UUID,
    mayorista: Mayorista = Depends(get_current_mayorista),
    prenda_service: PrendaService = Depends(_get_prenda_service),
):
    try:
        await prenda_service.eliminar(prenda_id, mayorista.id)
    except PrendaNoEncontradaError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prenda no encontrada",
        )
