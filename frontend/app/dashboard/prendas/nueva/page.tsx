"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ImageDropzone } from "@/components/prendas/ImageDropzone";
import { UploadProgress } from "@/components/prendas/UploadProgress";
import { subirPrenda } from "@/lib/api/prendas";
import { toast } from "sonner";

export default function NuevaPrendaPage() {
  const router = useRouter();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string>();
  const [nombre, setNombre] = useState("");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState<
    "idle" | "uploading" | "done" | "error"
  >("idle");
  const [uploadError, setUploadError] = useState<string | null>(null);

  const handleFileSelected = (selectedFile: File) => {
    setFile(selectedFile);
    setFileError(undefined);
  };

  const handleNext = () => {
    if (!file) {
      setFileError("Selecciona una imagen primero");
      return;
    }
    setStep(2);
  };

  const handleConfirm = async () => {
    if (!file) return;

    try {
      setStep(3);
      setUploadStatus("uploading");
      setUploadProgress(0);
      setUploadError(null);

      const prenda = await subirPrenda(
        file,
        nombre || undefined,
        (percent) => setUploadProgress(percent)
      );

      setUploadStatus("done");
      toast.success("Prenda subida correctamente");
      setTimeout(
        () =>
          router.push(
            `/dashboard/generacion/model-selector?prendaId=${prenda.id}`
          ),
        1000
      );
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Error inesperado al subir";
      if (message.includes("Límite mensual")) {
        toast.error("Límite mensual alcanzado. Considera actualizar tu plan.");
      } else {
        toast.error(message);
      }
      setUploadError(message);
      setUploadStatus("error");
    }
  };

  return (
    <div className="max-w-xl mx-auto space-y-6 py-8">
      <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
        Nueva prenda
      </h1>

      {step === 1 && (
        <div className="space-y-4">
          <ImageDropzone onFileSelected={handleFileSelected} error={fileError} />
          <Button onClick={handleNext} disabled={!file} className="w-full">
            Continuar
          </Button>
        </div>
      )}

      {step === 2 && (
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
              Nombre (opcional)
            </label>
            <Input
              value={nombre}
              onChange={(e) => setNombre(e.target.value.slice(0, 80))}
              placeholder="Prenda #N"
              maxLength={80}
            />
            <p className="text-xs text-zinc-400 mt-1 text-right">
              {nombre.length}/80
            </p>
          </div>
          <div className="flex gap-3">
            <Button
              variant="outline"
              onClick={() => setStep(1)}
              className="flex-1"
            >
              Atrás
            </Button>
            <Button onClick={handleConfirm} className="flex-1">
              Subir prenda
            </Button>
          </div>
        </div>
      )}

      {step === 3 && (
        <UploadProgress
          progress={uploadProgress}
          status={uploadStatus}
          errorMessage={uploadError ?? undefined}
        />
      )}
    </div>
  );
}
