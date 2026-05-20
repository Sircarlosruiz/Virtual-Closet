"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { PrendaGrid } from "@/components/prendas/PrendaGrid";
import { usePrendas } from "@/hooks/usePrendas";
import { useQueryClient } from "@tanstack/react-query";

export function DashboardContent() {
  const queryClient = useQueryClient();
  const { prendas, isLoading, fetchNextPage, hasNextPage } = usePrendas();

  const handleDelete = (id: string) => {
    queryClient.setQueryData(["prendas"], (prev: any) => ({
      items: (prev?.items || []).filter((p: any) => p.id !== id),
      next_cursor: prev?.next_cursor,
    }));
  };

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

      <PrendaGrid prendas={prendas} isLoading={isLoading} onDelete={handleDelete} />

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
