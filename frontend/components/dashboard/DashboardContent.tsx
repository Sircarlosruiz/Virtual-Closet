"use client";

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
    <>
      <PrendaGrid prendas={prendas} isLoading={isLoading} onDelete={handleDelete} />

      {hasNextPage && (
        <div className="mt-6 flex justify-center">
          <Button variant="outline" onClick={() => fetchNextPage()}>
            Cargar más
          </Button>
        </div>
      )}
    </>
  );
}
