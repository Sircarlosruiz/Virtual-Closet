"use client";

import { useCallback, useEffect, useState } from "react";
import { ExtractedGarment, getExtractedGarments } from "@/lib/api/extracted-garments";
import { ExtractedGarmentCard } from "./extracted-garment-card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { ArrowUpRight, Shirt } from "lucide-react";
import { useRouter } from "next/navigation";
import Link from "next/link";

const GARMENT_LABELS: Record<string, string> = {
  upper: "Upper Garment",
  lower: "Lower Garment",
  dress: "Full Dress",
};

export function ExtractedGarmentsGrid() {
  const router = useRouter();
  const [items, setItems] = useState<ExtractedGarment[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selectedGarment, setSelectedGarment] = useState<ExtractedGarment | null>(null);

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

  const handleUseInVton = (garmentId: string) => {
    router.push(`/dashboard/generate?garment_id=${garmentId}`);
  };

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
        <Link href="/dashboard/tryoff/new">
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
            onOpenDetail={setSelectedGarment}
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

      <Sheet open={!!selectedGarment} onOpenChange={(open) => !open && setSelectedGarment(null)}>
        <SheetContent>
          {selectedGarment && (
            <>
              <SheetHeader>
                <SheetTitle>Prenda Extraída</SheetTitle>
                <SheetDescription>
                  {GARMENT_LABELS[selectedGarment.garment_type] ?? selectedGarment.garment_type}
                </SheetDescription>
              </SheetHeader>
              <div className="mt-6 space-y-4">
                <div className="rounded-lg border overflow-hidden">
                  <img
                    src={selectedGarment.presigned_url}
                    alt={selectedGarment.filename}
                    className="w-full aspect-square object-cover"
                  />
                </div>

                <div className="flex items-center gap-2">
                  <Badge variant="secondary">
                    {GARMENT_LABELS[selectedGarment.garment_type]}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {new Date(selectedGarment.created_at).toLocaleDateString()}
                  </span>
                </div>

                <Button
                  className="w-full gap-2"
                  onClick={() => handleUseInVton(selectedGarment.id)}
                >
                  Use in VTON
                  <ArrowUpRight className="w-4 h-4" />
                </Button>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </>
  );
}
