"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Loader2, Plus, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { GarmentUploader } from "@/components/vton/GarmentUploader";
import { ModelSelector } from "@/components/vton/ModelSelector";
import { ClothTypeSelector } from "@/components/vton/ClothTypeSelector";
import { createBatch } from "@/lib/api/batches";
import type { BatchItemCreate } from "@/lib/api/batches";

type ClothType = "upper_body" | "lower_body" | "dress";

interface Pairing {
  garmentId: string;
  modelId: string | null;
  clothType: ClothType | null;
}

const MAX_ITEMS = 100;

export default function BatchCreatePage() {
  const router = useRouter();

  const [batchName, setBatchName] = useState("");
  const [pairings, setPairings] = useState<Pairing[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const canSubmit =
    pairings.length > 0 &&
    pairings.every((p) => p.modelId && p.clothType) &&
    !isSubmitting;

  const handleGarmentUploaded = useCallback((garmentId: string) => {
    setPairings((prev) => {
      if (prev.length >= MAX_ITEMS) {
        toast.error(`Máximo ${MAX_ITEMS} elementos por lote`);
        return prev;
      }
      return [...prev, { garmentId, modelId: null, clothType: null }];
    });
  }, []);

  const handleRemovePairing = useCallback((index: number) => {
    setPairings((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const handleModelSelected = useCallback((index: number, modelId: string) => {
    setPairings((prev) =>
      prev.map((p, i) => (i === index ? { ...p, modelId } : p))
    );
  }, []);

  const handleClothTypeSelected = useCallback(
    (index: number, clothType: ClothType) => {
      setPairings((prev) =>
        prev.map((p, i) => (i === index ? { ...p, clothType } : p))
      );
    },
    []
  );

  const handleSubmit = useCallback(async () => {
    if (!canSubmit) return;

    setIsSubmitting(true);
    try {
      const items: BatchItemCreate[] = pairings.map((p) => ({
        garment_id: p.garmentId,
        model_id: p.modelId!,
        cloth_type: p.clothType!,
      }));

      const result = await createBatch({
        name: batchName || undefined,
        items,
      });

      toast.success("Lote creado exitosamente");
      router.push(`/batches/${result.id}`);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Error al crear el lote";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }, [canSubmit, pairings, batchName, router]);

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Crear Lote de Pruebas Virtuales</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Selecciona prendas, empareja con modelos y envía hasta {MAX_ITEMS} trabajos a la vez
        </p>
      </div>

      {/* Batch name */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Nombre del Lote (opcional)</CardTitle>
          <CardDescription>
            Dale un nombre descriptivo para identificarlo más tarde
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Input
            placeholder="Ej: Colección Verano 2026"
            value={batchName}
            onChange={(e) => setBatchName(e.target.value)}
            maxLength={100}
          />
        </CardContent>
      </Card>

      {/* Pairings */}
      {pairings.map((pairing, index) => (
        <Card key={pairing.garmentId}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-lg">
              Emparejamiento {index + 1}
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleRemovePairing(index)}
            >
              <X className="w-4 h-4" />
            </Button>
          </CardHeader>
          <CardContent className="space-y-4">
            <ModelSelector
              onSelected={(id) => handleModelSelected(index, id)}
              selectedId={pairing.modelId ?? undefined}
            />
            <ClothTypeSelector
              onSelected={(type) => handleClothTypeSelected(index, type)}
              selected={pairing.clothType}
            />
          </CardContent>
        </Card>
      ))}

      {/* Add garment */}
      {pairings.length < MAX_ITEMS && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">
              Agregar Prenda ({pairings.length}/{MAX_ITEMS})
            </CardTitle>
            <CardDescription>
              {pairings.length === 0
                ? "Sube la primera prenda para comenzar"
                : `Agrega otra prenda al lote (${MAX_ITEMS - pairings.length} restantes)`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <GarmentUploader onUploaded={handleGarmentUploaded} />
          </CardContent>
        </Card>
      )}

      {/* Submit */}
      <Card>
        <CardContent className="pt-6">
          <Button
            className="w-full"
            size="lg"
            disabled={!canSubmit}
            onClick={handleSubmit}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Creando lote...
              </>
            ) : (
              <>
                <Plus className="w-4 h-4 mr-2" />
                Crear Lote ({pairings.length}{" "}
                {pairings.length === 1 ? "emparejamiento" : "emparejamientos"})
              </>
            )}
          </Button>

          {!canSubmit && !isSubmitting && pairings.length === 0 && (
            <p className="text-xs text-muted-foreground text-center mt-2">
              Sube al menos una prenda para comenzar
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
