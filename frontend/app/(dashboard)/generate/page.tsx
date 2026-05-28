"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { GarmentUploader } from "@/components/vton/GarmentUploader";
import { ModelSelector } from "@/components/vton/ModelSelector";
import { ClothTypeSelector } from "@/components/vton/ClothTypeSelector";
import { apiFetch } from "@/lib/api";

type ClothType = "upper_body" | "lower_body" | "dress";

export default function GeneratePage() {
  const router = useRouter();

  const [garmentId, setGarmentId] = useState<string | null>(null);
  const [modelId, setModelId] = useState<string | null>(null);
  const [clothType, setClothType] = useState<ClothType | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const canSubmit = Boolean(garmentId && modelId && clothType) && !isSubmitting;

  const handleSubmit = useCallback(async () => {
    if (!canSubmit) return;

    setIsSubmitting(true);
    try {
      const result = await apiFetch("/api/vton/generate", {
        method: "POST",
        body: JSON.stringify({
          garment_id: garmentId,
          model_id: modelId,
          cloth_type: clothType,
        }),
      });

      const jobId = result.job_id ?? result.id;
      if (jobId) {
        toast.success("Generación iniciada");
        router.push(`/dashboard/jobs/${jobId}`);
      } else {
        toast.error("Respuesta inesperada del servidor");
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Error al iniciar la generación";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }, [canSubmit, garmentId, modelId, clothType, router]);

  return (
    <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Generar Prueba Virtual</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Sube una prenda, selecciona un modelo y elige el tipo de ropa
        </p>
      </div>

      {/* Step 1: Garment Upload */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">1. Sube la Prenda</CardTitle>
          <CardDescription>
            Arrastra o selecciona una foto de la prenda (JPG/PNG, máx 10MB)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <GarmentUploader
            onUploaded={setGarmentId}
            onClear={() => setGarmentId(null)}
            uploadedId={garmentId}
          />
        </CardContent>
      </Card>

      {/* Step 2: Model Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">2. Selecciona el Modelo</CardTitle>
          <CardDescription>
            Elige entre tus propios modelos o la biblioteca curada
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ModelSelector onSelected={setModelId} selectedId={modelId} />
        </CardContent>
      </Card>

      {/* Step 3: Cloth Type + Submit */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">3. Tipo de Prenda</CardTitle>
          <CardDescription>
            Indica qué tipo de prenda estás probando
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <ClothTypeSelector onSelected={setClothType} selected={clothType} />

          <Button
            className="w-full"
            size="lg"
            disabled={!canSubmit}
            onClick={handleSubmit}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Iniciando generación...
              </>
            ) : (
              "Generar prueba virtual"
            )}
          </Button>

          {!canSubmit && !isSubmitting && (
            <p className="text-xs text-muted-foreground text-center">
              {!garmentId && "Sube una prenda"}
              {garmentId && !modelId && "Selecciona un modelo"}
              {garmentId && modelId && !clothType && "Selecciona el tipo de prenda"}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
