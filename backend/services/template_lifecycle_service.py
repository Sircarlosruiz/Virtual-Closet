from uuid import UUID

from api.schemas.template import ImageTemplateCreateRequest, ImageTemplateUpdateRequest
from models.image_template import ImageTemplate, TemplateReference
from repositories.image_template_repo import ImageTemplateRepository


class TemplateNotFoundError(Exception):
    pass


class TemplateArchivedError(Exception):
    """Raised when attempting to revise an archived template."""


class TemplateLifecycleService:
    def __init__(self, repository: ImageTemplateRepository) -> None:
        self._repository = repository

    async def create_template(
        self, created_by: UUID, request: ImageTemplateCreateRequest
    ) -> ImageTemplate:
        template = ImageTemplate(
            scope=request.scope.value,
            wholesaler_id=request.wholesaler_id,
            version=1,
            status="draft",
            name=request.name,
            model=request.model,
            background=request.background,
            colors=request.colors,
            rack=request.rack,
            prompt=request.prompt,
            created_by=created_by,
            references=[
                TemplateReference(storage_key=ref.storage_key, label=ref.label)
                for ref in request.references
            ],
        )
        return await self._repository.create(template)

    async def revise_template(
        self, template_id: UUID, request: ImageTemplateUpdateRequest
    ) -> ImageTemplate:
        template = await self._repository.get_for_lock(template_id)
        if template is None:
            raise TemplateNotFoundError(f"Template {template_id} not found")
        if template.status == "archived":
            raise TemplateArchivedError(f"Template {template_id} is archived")

        if request.name is not None:
            template.name = request.name
        if request.model is not None:
            template.model = request.model
        if request.background is not None:
            template.background = request.background
        if request.colors is not None:
            template.colors = request.colors
        if request.rack is not None:
            template.rack = request.rack
        if request.prompt is not None:
            template.prompt = request.prompt
        if request.references is not None:
            template.references = [
                TemplateReference(storage_key=ref.storage_key, label=ref.label)
                for ref in request.references
            ]

        template.version += 1
        return await self._repository.save(template)

    async def archive_template(self, template_id: UUID) -> ImageTemplate:
        template = await self._repository.archive(template_id)
        if template is None:
            raise TemplateNotFoundError(f"Template {template_id} not found")
        return template

    async def get_by_id(self, template_id: UUID) -> ImageTemplate:
        template = await self._repository.get_by_id(template_id)
        if template is None:
            raise TemplateNotFoundError(f"Template {template_id} not found")
        return template

    async def list_administrative(
        self,
        scope: str | None = None,
        wholesaler_id: UUID | None = None,
        status: str | None = None,
    ) -> list[ImageTemplate]:
        return await self._repository.list_administrative(scope, wholesaler_id, status)

    async def list_selectable(self, wholesaler_id: UUID) -> list[ImageTemplate]:
        return await self._repository.list_selectable(wholesaler_id)
