from uuid import UUID, uuid4

from models.prenda import Prenda
from repositories.prenda_repo import PrendaRepository
from services.storage_service import StorageService


class LimiteMensualAlcanzadoError(Exception):
    pass


class PrendaNoEncontradaError(Exception):
    pass


class PrendaService:
    LIMITE_PRENDAS_BASE = 40

    def __init__(self, prenda_repo: PrendaRepository, storage_service: StorageService):
        self.prenda_repo = prenda_repo
        self.storage_service = storage_service

    async def iniciar_subida(self, mayorista_id: UUID, extension: str) -> dict:
        count = await self.prenda_repo.count_this_month(mayorista_id)
        if count >= self.LIMITE_PRENDAS_BASE:
            raise LimiteMensualAlcanzadoError()

        prenda_id = uuid4()
        object_key = f"{mayorista_id}/{prenda_id}/original.{extension}"
        upload_url = await self.storage_service.generate_upload_url(object_key)
        return {"upload_url": upload_url, "prenda_id": prenda_id, "object_key": object_key}

    async def confirmar_subida(
        self, mayorista_id: UUID, prenda_id: UUID, nombre: str, object_key: str
    ) -> Prenda:
        imagen_url = await self.storage_service.generate_download_url(object_key)
        nombre_final = nombre or f"Prenda #{prenda_id.hex[:6]}"
        return await self.prenda_repo.create(
            mayorista_id,
            nombre_final,
            imagen_url,
            prenda_id=prenda_id,
            estado="lista",
        )

    async def actualizar_nombre(
        self, prenda_id: UUID, mayorista_id: UUID, nombre: str
    ) -> Prenda:
        prenda = await self.prenda_repo.update_nombre(prenda_id, mayorista_id, nombre)
        if prenda is None:
            raise PrendaNoEncontradaError()
        return prenda

    async def listar(
        self, mayorista_id: UUID, cursor: UUID | None
    ) -> list[Prenda]:
        return await self.prenda_repo.list_by_mayorista(mayorista_id, cursor)

    async def eliminar(self, prenda_id: UUID, mayorista_id: UUID) -> None:
        prenda = await self.prenda_repo.get_by_id(prenda_id, mayorista_id)
        if prenda is None:
            raise PrendaNoEncontradaError()

        await self.prenda_repo.delete(prenda_id, mayorista_id)

        url = prenda.imagen_original_url
        if "/originals/" in url:
            key = url.split("/originals/")[-1].split("?")[0]
            await self.storage_service.delete_object(key)
