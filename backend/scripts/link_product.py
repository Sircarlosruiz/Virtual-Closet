"""Create an explicit product link between an external product and Virtual Closet.

Ownership is never inferred from an external identifier: this record is the
authoritative mapping used by the generation bridge.

Uso:
    cd backend
    uv run python scripts/link_product.py \
        --system bfashion --external-product-id 12345 \
        --mayorista-email dueno@negocio.com --tenant-slug mi-tenant

Opcionales:
    --external-wholesaler-id WH-9
    --prenda-id <uuid de la prenda en Virtual Closet>
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.database import async_session
from models.product_link import ProductLink
from repositories.mayorista_repo import MayoristaRepository
from repositories.product_link_repo import ProductLinkRepository
from repositories.tenant_repo import TenantRepo


async def link_product(
    system: str,
    external_product_id: str,
    external_wholesaler_id: str | None,
    mayorista_email: str,
    tenant_slug: str,
    prenda_id: str | None,
) -> None:
    async with async_session() as db:
        tenant = await TenantRepo(db).get_by_slug(tenant_slug)
        if tenant is None:
            raise RuntimeError(f"No existe un tenant con slug '{tenant_slug}'")

        mayorista = await MayoristaRepository(db).get_by_email(mayorista_email.lower())
        if mayorista is None:
            raise RuntimeError(f"No existe un mayorista con email '{mayorista_email}'")
        if mayorista.tenant_id != tenant.id:
            raise RuntimeError("El mayorista no pertenece al tenant indicado")

        repo = ProductLinkRepository(db)
        if await repo.get_by_external_product(system, external_product_id) is not None:
            raise RuntimeError(
                f"Ya existe un product link para {system}/{external_product_id}"
            )

        link = await repo.create(
            ProductLink(
                system=system,
                external_product_id=external_product_id,
                external_wholesaler_id=external_wholesaler_id,
                mayorista_id=mayorista.id,
                prenda_id=UUID(prenda_id) if prenda_id else None,
                tenant_id=tenant.id,
                is_active=True,
                created_by=mayorista.id,
            )
        )
        print("Product link creado.")
        print(f"  id:                  {link.id}")
        print(f"  system:              {link.system}")
        print(f"  external_product_id: {link.external_product_id}")
        print(f"  mayorista_id:        {link.mayorista_id}")
        print(f"  tenant_id:           {link.tenant_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system", required=True)
    parser.add_argument("--external-product-id", required=True)
    parser.add_argument("--external-wholesaler-id", default=None)
    parser.add_argument("--mayorista-email", required=True)
    parser.add_argument("--tenant-slug", required=True)
    parser.add_argument("--prenda-id", default=None)
    args = parser.parse_args()
    asyncio.run(
        link_product(
            system=args.system,
            external_product_id=args.external_product_id,
            external_wholesaler_id=args.external_wholesaler_id,
            mayorista_email=args.mayorista_email,
            tenant_slug=args.tenant_slug,
            prenda_id=args.prenda_id,
        )
    )


if __name__ == "__main__":
    main()
