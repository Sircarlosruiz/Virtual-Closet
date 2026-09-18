"""Provision an authenticated service client for server-to-server integration.

The raw secret is printed exactly once and never persisted in clear text.

Uso:
    cd backend
    uv run python scripts/provision_service_client.py \
        --name bfashion --system bfashion --tenant-slug mi-tenant

Docker:
    docker compose exec fastapi uv run python scripts/provision_service_client.py ...
"""

from __future__ import annotations

import argparse
import asyncio
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.database import async_session
from core.security import hash_password
from models.service_client import ServiceClient
from repositories.service_client_repo import ServiceClientRepository
from repositories.tenant_repo import TenantRepo


async def provision(name: str, system: str, tenant_slug: str) -> None:
    async with async_session() as db:
        tenant = await TenantRepo(db).get_by_slug(tenant_slug)
        if tenant is None:
            raise RuntimeError(f"No existe un tenant con slug '{tenant_slug}'")

        repo = ServiceClientRepository(db)
        if await repo.get_by_name(name) is not None:
            raise RuntimeError(f"Ya existe un service client llamado '{name}'")

        raw_secret = secrets.token_urlsafe(48)
        client = await repo.create(
            ServiceClient(
                name=name,
                system=system,
                secret_hash=hash_password(raw_secret),
                tenant_id=tenant.id,
                is_active=True,
            )
        )

        print("Service client creado.")
        print(f"  id:     {client.id}")
        print(f"  name:   {client.name}")
        print(f"  system: {client.system}")
        print(f"  secret: {raw_secret}")
        print("Guarda el secret ahora; no se puede recuperar.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="Unique service client name")
    parser.add_argument("--system", required=True, help="External system key, e.g. bfashion")
    parser.add_argument("--tenant-slug", required=True, help="Tenant slug to scope this client to")
    args = parser.parse_args()
    asyncio.run(provision(args.name, args.system, args.tenant_slug))


if __name__ == "__main__":
    main()
