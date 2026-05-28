"use client";

import { useState } from "react";
import { useCatalogosList } from "@/hooks/useCatalogos";
import { CatalogCard } from "@/components/catalogos/CatalogCard";
import { CreateCatalogModal } from "@/components/catalogos/CreateCatalogModal";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";

export default function CatalogosPage() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const { data, isLoading, error } = useCatalogosList(1, 20);

  if (isLoading) {
    return (
      <div className="max-w-6xl mx-auto py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
            Catálogos
          </h1>
          <Button disabled>
            <Plus className="w-4 h-4 mr-2" />
            Crear catálogo
          </Button>
        </div>
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
      <div className="max-w-6xl mx-auto py-8">
        <div className="text-center py-12">
          <p className="text-red-600">Error al cargar catálogos</p>
          <p className="text-sm text-muted-foreground mt-2">{error.message}</p>
        </div>
      </div>
    );
  }

  const catalogs = data?.catalogs ?? [];

  return (
    <div className="max-w-6xl mx-auto py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
          Catálogos
        </h1>
        <Button onClick={() => setShowCreateModal(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Crear catálogo
        </Button>
      </div>

      {catalogs.length === 0 ? (
        <div className="text-center py-12 border-2 border-dashed rounded-lg">
          <p className="text-lg font-medium text-zinc-700 dark:text-zinc-300">
            No tienes catálogos aún
          </p>
          <p className="text-sm text-muted-foreground mt-2 mb-4">
            Crea tu primer catálogo para empezar a organizar tus prendas
          </p>
          <Button onClick={() => setShowCreateModal(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Crear tu primer catálogo
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {catalogs.map((catalogo) => (
            <CatalogCard key={catalogo.id} catalogo={catalogo} />
          ))}
        </div>
      )}

      <CreateCatalogModal
        open={showCreateModal}
        onOpenChange={setShowCreateModal}
      />
    </div>
  );
}
