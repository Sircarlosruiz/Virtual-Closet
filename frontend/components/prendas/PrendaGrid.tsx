"use client";

import { PrendaResponse } from "@/lib/api/prendas";
import { PrendaCard } from "./PrendaCard";
import Link from "next/link";
import { Button } from "@/components/ui/button";

interface PrendaGridProps {
  prendas: PrendaResponse[];
  isLoading: boolean;
  onDelete?: (id: string) => void;
}

export function PrendaGrid({ prendas, isLoading, onDelete }: PrendaGridProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="aspect-square bg-zinc-200 dark:bg-zinc-800 rounded-lg animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (prendas.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="text-6xl mb-4">👕</div>
        <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
          No tienes prendas aún
        </h3>
        <p className="text-zinc-500 dark:text-zinc-400 mt-1 mb-4">
          Sube tu primera prenda para comenzar
        </p>
        <Link href="/dashboard/prendas/nueva">
          <Button>Subir primera prenda</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      {prendas.map((prenda) => (
        <PrendaCard key={prenda.id} prenda={prenda} onDelete={onDelete} />
      ))}
    </div>
  );
}
