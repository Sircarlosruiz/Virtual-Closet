"use client";

import { useCallback, useId, useState } from "react";
import imageCompression from "browser-image-compression";

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/heic"];
const MAX_SIZE_MB = 20;

interface ImageDropzoneProps {
  onFileSelected: (file: File) => void;
  error?: string;
  onValidationError?: (message: string) => void;
}

function isAcceptedFile(file: File): boolean {
  if (ACCEPTED_TYPES.includes(file.type)) {
    return true;
  }
  const ext = file.name.split(".").pop()?.toLowerCase();
  return ext === "jpg" || ext === "jpeg" || ext === "png" || ext === "heic";
}

export function ImageDropzone({
  onFileSelected,
  error,
  onValidationError,
}: ImageDropzoneProps) {
  const inputId = useId();
  const [preview, setPreview] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const handleFile = useCallback(
    async (file: File) => {
      setLocalError(null);

      if (!isAcceptedFile(file)) {
        const message = "Formato no soportado. Usa JPG, PNG o HEIC.";
        setLocalError(message);
        onValidationError?.(message);
        return;
      }
      if (file.size > MAX_SIZE_MB * 1024 * 1024) {
        const message = `La imagen supera ${MAX_SIZE_MB} MB.`;
        setLocalError(message);
        onValidationError?.(message);
        return;
      }

      setProcessing(true);
      try {
        let uploadFile = file;
        try {
          uploadFile = await imageCompression(file, {
            maxSizeMB: 5,
            maxWidthOrHeight: 1024,
            useWebWorker: false,
            preserveExif: false,
          });
        } catch {
          uploadFile = file;
        }

        setPreview(URL.createObjectURL(uploadFile));
        onFileSelected(uploadFile);
      } catch {
        const message =
          "No se pudo procesar la imagen. Prueba con JPG o PNG.";
        setLocalError(message);
        onValidationError?.(message);
      } finally {
        setProcessing(false);
      }
    },
    [onFileSelected, onValidationError]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  return (
    <div className="w-full">
      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        className="border-2 border-dashed border-zinc-300 dark:border-zinc-600 rounded-lg p-8 text-center cursor-pointer hover:border-zinc-400 dark:hover:border-zinc-500 transition-colors"
        onClick={() => !processing && document.getElementById(inputId)?.click()}
      >
        {processing ? (
          <div className="text-zinc-500 dark:text-zinc-400">
            <p className="text-lg font-medium">Procesando imagen...</p>
          </div>
        ) : preview ? (
          <img
            src={preview}
            alt="Preview"
            className="max-h-64 mx-auto rounded-lg object-contain"
          />
        ) : (
          <div className="text-zinc-500 dark:text-zinc-400">
            <p className="text-lg font-medium">Arrastra una imagen aquí</p>
            <p className="text-sm mt-1">o haz clic para seleccionar</p>
            <p className="text-xs mt-2 text-zinc-400">JPG, PNG, HEIC (max 20MB)</p>
          </div>
        )}
        <input
          id={inputId}
          type="file"
          accept=".jpg,.jpeg,.png,.heic,image/jpeg,image/png,image/heic"
          className="hidden"
          disabled={processing}
          onChange={handleChange}
        />
      </div>
      {(error || localError) && (
        <p className="text-red-500 text-sm mt-2">{error || localError}</p>
      )}
    </div>
  );
}
