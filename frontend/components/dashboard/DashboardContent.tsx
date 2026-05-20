"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { PrendaGrid } from "@/components/prendas/PrendaGrid";
import { usePrendas } from "@/hooks/usePrendas";

export function DashboardContent() {
  const { prendas, isLoading, fetchNextPage, hasNextPage } = usePrendas();

  return (
    <div className="flex flex-1 flex-col p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
          Mis prendas
        </h1>
        <Link href="/dashboard/prendas/nueva">
          <Button>Nueva prenda</Button>
        </Link>
      </div>

      <PrendaGrid prendas={prendas} isLoading={isLoading} />

      {hasNextPage && (
        <div className="flex justify-center mt-6">
          <Button variant="outline" onClick={() => fetchNextPage()}>
            Cargar más
          </Button>
        </div>
      )}
    </div>
  );
}
