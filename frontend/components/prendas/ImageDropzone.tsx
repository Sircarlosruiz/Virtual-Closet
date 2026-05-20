"use client";

import { useCallback, useState } from "react";
import imageCompression from "browser-image-compression";

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/heic"];
const MAX_SIZE_MB = 20;

interface ImageDropzoneProps {
  onFileSelected: (file: File) => void;
  error?: string;
}

export function ImageDropzone({ onFileSelected, error }: ImageDropzoneProps) {
  const [preview, setPreview] = useState<string | null>(null);

  const handleFile = useCallback(
    async (file: File) => {
      if (!ACCEPTED_TYPES.includes(file.type)) {
        return;
      }
      if (file.size > MAX_SIZE_MB * 1024 * 1024) {
        return;
      }

      if (file.type === "image/heic") {
        const supported = URL.createObjectURL(file);
        const img = new Image();
        img.onerror = () => {
          URL.revokeObjectURL(supported);
        };
        img.src = supported;
      }

      const compressed = await imageCompression(file, {
        maxSizeMB: 5,
        maxWidthOrHeight: 1024,
        useWebWorker: true,
      });

      setPreview(URL.createObjectURL(compressed));
      onFileSelected(compressed);
    },
    [onFileSelected]
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
        onClick={() => document.getElementById("file-input")?.click()}
      >
        {preview ? (
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
          id="file-input"
          type="file"
          accept=".jpg,.jpeg,.png,.heic"
          className="hidden"
          onChange={handleChange}
        />
      </div>
      {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
    </div>
  );
}
