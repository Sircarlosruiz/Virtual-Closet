import asyncio
from uuid import UUID, uuid4

from core.minio_buckets import ensure_minio_buckets
from models.prenda import Prenda
from repositories.prenda_repo import PrendaRepository
from services.storage_service import StorageService


class LimiteMensualAlcanzadoError(Exception):
    pass


class PrendaNoEncontradaError(Exception):
    pass


class FormatoImagenNoSoportadoError(Exception):
    pass


_EXTENSION_BY_CONTENT_TYPE = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/heic": "heic",
    "image/heif": "heic",
}


class PrendaService:
    LIMITE_PRENDAS_BASE = 40

    def __init__(self, prenda_repo: PrendaRepository, storage_service: StorageService):
        self.prenda_repo = prenda_repo
        self.storage_service = storage_service

    def _extension_from_upload(self, filename: str | None, content_type: str | None) -> str:
        if content_type:
            normalized = content_type.split(";", 1)[0].strip().lower()
            if normalized in _EXTENSION_BY_CONTENT_TYPE:
                return _EXTENSION_BY_CONTENT_TYPE[normalized]
        if filename and "." in filename:
            ext = filename.rsplit(".", 1)[-1].lower()
            if ext == "jpeg":
                return "jpg"
            if ext in ("jpg", "png", "heic"):
                return ext
        raise FormatoImagenNoSoportadoError()

    async def subir_prenda(
        self,
        mayorista_id: UUID,
        file_bytes: bytes,
        filename: str | None,
        content_type: str | None,
        nombre: str,
    ) -> Prenda:
        await ensure_minio_buckets()
        count = await self.prenda_repo.count_this_month(mayorista_id)
        if count >= self.LIMITE_PRENDAS_BASE:
            raise LimiteMensualAlcanzadoError()

        extension = self._extension_from_upload(filename, content_type)
        prenda_id = uuid4()
        object_key = f"{mayorista_id}/{prenda_id}/original.{extension}"
        await self.storage_service.upload_bytes(
            object_key,
            file_bytes,
            content_type=content_type or "image/jpeg",
            bucket_override="originals",
        )
        imagen_url = await self.storage_service.generate_download_url(object_key)
        nombre_final = nombre or f"Prenda #{prenda_id.hex[:6]}"
        return await self.prenda_repo.create(
            mayorista_id,
            nombre_final,
            imagen_url,
            imagen_original_key=object_key,
            prenda_id=prenda_id,
            estado="lista",
        )

    async def iniciar_subida(self, mayorista_id: UUID, extension: str) -> dict:
        await ensure_minio_buckets()
        count = await self.prenda_repo.count_this_month(mayorista_id)
        if count >= self.LIMITE_PRENDAS_BASE:
            raise LimiteMensualAlcanzadoError()

        prenda_id = uuid4()
        object_key = f"{mayorista_id}/{prenda_id}/original.{extension}"
        upload_url = await self.storage_service.generate_upload_url(
            object_key, bucket_override="originals"
        )
        return {"upload_url": upload_url, "prenda_id": prenda_id, "object_key": object_key}

    async def confirmar_subida(
        self, mayorista_id: UUID, prenda_id: UUID, nombre: str, object_key: str
    ) -> Prenda:
        await ensure_minio_buckets()
        exists = False
        for _ in range(5):
            if await self.storage_service.object_exists(object_key, bucket_override="originals"):
                exists = True
                break
            await asyncio.sleep(0.4)
        if not exists:
            raise ValueError(
                "La imagen no se guardó en MinIO. "
                "Comprueba que MinIO esté en http://localhost:9000 y vuelve a subir la foto."
            )
        imagen_url = await self.storage_service.generate_download_url(object_key)
        nombre_final = nombre or f"Prenda #{prenda_id.hex[:6]}"
        return await self.prenda_repo.create(
            mayorista_id,
            nombre_final,
            imagen_url,
            imagen_original_key=object_key,
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

        key = prenda.imagen_original_key or (
            self.storage_service.key_from_originals_url(prenda.imagen_original_url)
            if "/originals/" in prenda.imagen_original_url
            else None
        )
        if key:
            await self.storage_service.delete_object(key)
