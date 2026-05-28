"use client";

import Link from "next/link";
import { usePortalCatalogsList } from "@/hooks/usePortal";
import { PortalCatalogCard } from "@/components/portal/PortalCatalogCard";

export default function PortalPage() {
  const { data, isLoading, error } = usePortalCatalogsList(1, 20);

  if (isLoading) {
    return (
      <div className="max-w-6xl mx-auto py-8 px-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-32 bg-zinc-200 dark:bg-zinc-800 rounded-lg animate-pulse"
            />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-6xl mx-auto py-8 px-4">
        <div className="text-center py-12">
          <p className="text-red-600">Error al cargar catálogos</p>
          <p className="text-sm text-muted-foreground mt-2">
            Tu sesión puede haber expirado.
          </p>
          <Link
            href="/portal/request-link"
            className="mt-4 inline-block px-4 py-2 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 rounded-lg hover:opacity-90 transition-opacity"
          >
            Solicitar nuevo enlace
          </Link>
        </div>
      </div>
    );
  }

  const catalogs = data?.catalogs ?? [];

  if (catalogs.length === 0) {
    return (
      <div className="max-w-6xl mx-auto py-8 px-4">
        <div className="text-center py-12">
          <p className="text-lg font-medium text-zinc-700 dark:text-zinc-300">
            No hay colecciones disponibles
          </p>
          <p className="text-sm text-muted-foreground mt-2">
            Vuelve más tarde para ver nuevas colecciones.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto py-8 px-4">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50 mb-6">
        Colecciones publicadas
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {catalogs.map((catalog) => (
          <PortalCatalogCard key={catalog.id} catalog={catalog} />
        ))}
      </div>
    </div>
  );
}
