"use client";

import { useCallback, useState } from "react";
import { toast } from "sonner";
import { Upload, CheckCircle2, X, Image as ImageIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

const ACCEPTED_TYPES = ["image/jpeg", "image/png"];
const MAX_SIZE = 10 * 1024 * 1024; // 10MB

interface GarmentUploaderProps {
  onUploaded: (garmentId: string) => void;
  onClear?: () => void;
  uploadedId?: string | null;
  previewUrl?: string | null;
}

function validateFile(file: File): string | null {
  if (!ACCEPTED_TYPES.includes(file.type)) {
    return "Solo se permiten imágenes JPG o PNG";
  }
  if (file.size > MAX_SIZE) {
    return "La imagen no debe superar 10MB";
  }
  return null;
}

export function GarmentUploader({
  onUploaded,
  onClear,
  uploadedId,
  previewUrl,
}: GarmentUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [localPreview, setLocalPreview] = useState<string | null>(previewUrl ?? null);
  const [error, setError] = useState<string | null>(null);

  const handleFile = useCallback(
    async (file: File) => {
      setError(null);

      const validationError = validateFile(file);
      if (validationError) {
        setError(validationError);
        return;
      }

      // Show local preview immediately
      const objectUrl = URL.createObjectURL(file);
      setLocalPreview(objectUrl);

      // Upload to backend
      setIsUploading(true);
      try {
        const formData = new FormData();
        formData.append("file", file);

        const result = await apiFetch("/api/media/garments", {
          method: "POST",
          body: formData,
        });

        const garmentId = result.id as string;
        onUploaded(garmentId);
        toast.success("Prenda subida correctamente");
      } catch (err) {
        const message = err instanceof Error ? err.message : "Error al subir la prenda";
        toast.error(message);
        setLocalPreview(null);
      } finally {
        setIsUploading(false);
      }
    },
    [onUploaded]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) {
        handleFile(file);
      }
    },
    [handleFile]
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        handleFile(file);
      }
    },
    [handleFile]
  );

  const handleClear = useCallback(() => {
    if (localPreview && !previewUrl) {
      URL.revokeObjectURL(localPreview);
    }
    setLocalPreview(null);
    setError(null);
    onClear?.();
  }, [localPreview, previewUrl, onClear]);

  // Already uploaded state
  if (uploadedId && localPreview) {
    return (
      <div className="relative">
        <div className="rounded-lg border border-border overflow-hidden">
          <img
            src={localPreview}
            alt="Prenda seleccionada"
            className="w-full h-48 object-cover"
          />
        </div>
        <div className="absolute top-2 right-2 flex gap-1">
          <span className="inline-flex items-center gap-1 bg-green-600 text-white text-xs px-2 py-1 rounded-full">
            <CheckCircle2 className="w-3 h-3" />
            Seleccionada
          </span>
          <Button
            variant="destructive"
            size="icon-xs"
            onClick={handleClear}
            aria-label="Quitar prenda seleccionada"
          >
            <X className="w-3 h-3" />
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div
        role="button"
        tabIndex={0}
        aria-label="Subir imagen de prenda"
        className={cn(
          "relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 transition-colors cursor-pointer",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
          isDragging && "border-primary bg-primary/5",
          isUploading && "pointer-events-none opacity-60",
          !isDragging && !isUploading && "border-border hover:border-primary/50"
        )}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => document.getElementById("garment-file-input")?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            document.getElementById("garment-file-input")?.click();
          }
        }}
      >
        {isUploading ? (
          <div className="flex flex-col items-center gap-2">
            <Upload className="w-8 h-8 text-muted-foreground animate-pulse" />
            <p className="text-sm text-muted-foreground">Subiendo...</p>
          </div>
        ) : localPreview ? (
          <div className="flex flex-col items-center gap-2">
            <img
              src={localPreview}
              alt="Vista previa de prenda"
              className="w-full h-48 object-cover rounded-lg"
            />
            <p className="text-sm text-muted-foreground">
              Click para cambiar la imagen
            </p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <ImageIcon className="w-8 h-8 text-muted-foreground" />
            <div className="text-center">
              <p className="text-sm font-medium">
                Arrastra una imagen o{" "}
                <span className="text-primary">selecciona un archivo</span>
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                JPG o PNG, máximo 10MB
              </p>
            </div>
          </div>
        )}
        <input
          id="garment-file-input"
          type="file"
          accept="image/jpeg,image/png"
          className="hidden"
          onChange={handleInputChange}
          aria-hidden="true"
        />
      </div>

      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
