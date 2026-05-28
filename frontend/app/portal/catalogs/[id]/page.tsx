"use client";

import { useParams, useRouter } from "next/navigation";
import { usePortalCatalog } from "@/hooks/usePortal";
import { PortalCatalogItemCard } from "@/components/portal/PortalCatalogItemCard";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";

export default function PortalCatalogDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const { data: catalog, isLoading, error } = usePortalCatalog(id);

  if (isLoading) {
    return (
      <div className="max-w-6xl mx-auto py-8 px-4">
        <div className="animate-pulse space-y-6">
          <div className="h-8 w-48 bg-zinc-200 dark:bg-zinc-800 rounded" />
          <div className="h-64 bg-zinc-200 dark:bg-zinc-800 rounded" />
        </div>
      </div>
    );
  }

  if (error || !catalog) {
    return (
      <div className="max-w-6xl mx-auto py-8 px-4">
        <div className="text-center py-12">
          <p className="text-red-600">Catálogo no disponible</p>
          <Button
            variant="outline"
            className="mt-4"
            onClick={() => router.push("/portal")}
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Volver
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto py-8 px-4">
      <Button
        variant="ghost"
        size="sm"
        className="mb-4"
        onClick={() => router.push("/portal")}
      >
        <ArrowLeft className="w-4 h-4 mr-2" />
        Colecciones
      </Button>

      <h2 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50 mb-6">
        {catalog.name}
      </h2>

      {catalog.items.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-zinc-600 dark:text-zinc-400">
            Esta colección aún no tiene prendas.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {catalog.items.map((item) => (
            <PortalCatalogItemCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
