"use client";

import { useValidateBuyerLink } from "@/hooks/useSettings";
import { PortalCatalogCard } from "@/components/portal/PortalCatalogCard";
import { usePortalCatalogsList } from "@/hooks/usePortal";
import Link from "next/link";

interface BuyerAccessValidatorProps {
  token: string;
}

export function BuyerAccessValidator({ token }: BuyerAccessValidatorProps) {
  const { data, isLoading, error } = useValidateBuyerLink(token);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <div className="h-8 w-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
        <p className="text-sm text-zinc-500 mt-4">Validando enlace...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600 font-medium">Error al validar el enlace</p>
        <p className="text-sm text-zinc-500 mt-2">
          No se pudo verificar el enlace. Intentá de nuevo.
        </p>
        <Link
          href="/portal/request-link"
          className="mt-4 inline-block px-4 py-2 bg-zinc-900 text-white rounded-lg hover:opacity-90 transition-opacity text-sm"
        >
          Solicitar nuevo enlace
        </Link>
      </div>
    );
  }

  if (!data?.valid) {
    const reason = data?.reason;
    const isExpired = reason === "link_expired";

    return (
      <div className="text-center py-12">
        <div className="mx-auto h-16 w-16 rounded-full bg-red-100 flex items-center justify-center mb-4">
          <svg
            className="h-8 w-8 text-red-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>
        <h2 className="text-xl font-semibold text-zinc-900 mb-2">
          {isExpired ? "Enlace expirado" : "Enlace inválido"}
        </h2>
        <p className="text-sm text-zinc-500 mb-6">
          {isExpired
            ? "Este enlace ha expirado. Contactá al mayorista para recibir uno nuevo."
            : "Enlace inválido. Contactá al remitente para recibir uno nuevo."}
        </p>
        <Link
          href="/portal/request-link"
          className="inline-block px-4 py-2 bg-zinc-900 text-white rounded-lg hover:opacity-90 transition-opacity text-sm"
        >
          Solicitar acceso
        </Link>
      </div>
    );
  }

  // Valid token — show catalogs
  return <BuyerCatalogList catalogIds={data.catalog_ids ?? []} />;
}

function BuyerCatalogList({ catalogIds }: { catalogIds: string[] }) {
  const { data, isLoading, error } = usePortalCatalogsList(1, 50);

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className="h-32 bg-zinc-200 rounded-lg animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600">Error al cargar catálogos</p>
      </div>
    );
  }

  const catalogs =
    data?.catalogs?.filter((c) => catalogIds.includes(c.id)) ?? [];

  if (catalogs.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-lg font-medium text-zinc-700">
          No hay catálogos disponibles
        </p>
        <p className="text-sm text-zinc-500 mt-2">
          Este enlace no tiene catálogos asignados.
        </p>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-xl font-semibold text-zinc-900 mb-6">
        Catálogos compartidos
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {catalogs.map((catalog) => (
          <PortalCatalogCard key={catalog.id} catalog={catalog} />
        ))}
      </div>
    </div>
  );
}
