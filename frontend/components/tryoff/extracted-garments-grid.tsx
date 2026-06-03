"use client";

import { useCallback, useEffect, useState } from "react";
import { ExtractedGarment, getExtractedGarments } from "@/lib/api/extracted-garments";
import { ExtractedGarmentCard } from "./extracted-garment-card";
import { GarmentPreviewModal } from "./garment-preview-modal";
import { Button } from "@/components/ui/button";
import { Shirt } from "lucide-react";
import Link from "next/link";

export function ExtractedGarmentsGrid() {
  const [items, setItems] = useState<ExtractedGarment[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selectedGarment, setSelectedGarment] = useState<ExtractedGarment | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);

  const loadGarments = useCallback(async () => {
    setLoading(true);
    try {
      const response = await getExtractedGarments(page, 24);
      setItems(response.items);
      setTotal(response.total);
    } catch {
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [page]);

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    loadGarments();
  }, [loadGarments]);
  /* eslint-enable react-hooks/set-state-in-effect */

  if (loading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div
            key={i}
            className="aspect-square bg-zinc-200 dark:bg-zinc-800 rounded-lg animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <Shirt className="w-16 h-16 text-muted-foreground mb-4" />
        <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
          No hay prendas extraídas
        </h3>
        <p className="text-zinc-500 dark:text-zinc-400 mt-1 mb-4">
          Extrae prendas de tus imágenes para verlas aquí
        </p>
        <Link href="/dashboard/extraction/new">
          <Button>Extraer tu primera prenda</Button>
        </Link>
      </div>
    );
  }

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {items.map((garment) => (
          <ExtractedGarmentCard
            key={garment.id}
            garment={garment}
            onOpenDetail={(g) => {
              setSelectedGarment(g);
              setPreviewOpen(true);
            }}
          />
        ))}
      </div>

      {items.length < total && (
        <div className="mt-6 flex justify-center">
          <Button variant="outline" onClick={() => setPage((p) => p + 1)}>
            Cargar más
          </Button>
        </div>
      )}

      {selectedGarment && (
        <GarmentPreviewModal
          imageUrl={selectedGarment.presigned_url}
          garmentType={selectedGarment.garment_type}
          mediaId={selectedGarment.id}
          jobId={selectedGarment.source_job_id ?? "unknown"}
          filename={selectedGarment.filename}
          open={previewOpen}
          onOpenChange={(open) => {
            setPreviewOpen(open);
            if (!open) setSelectedGarment(null);
          }}
        />
      )}
    </>
  );
}
