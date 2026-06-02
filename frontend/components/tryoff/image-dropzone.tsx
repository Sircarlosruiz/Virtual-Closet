"use client";

import { useCallback, useState, useRef } from "react";
import { X, Image as ImageIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const ACCEPTED_TYPES = ["image/jpeg", "image/png"];
const MAX_SIZE = 10 * 1024 * 1024; // 10MB

interface ImageDropzoneProps {
  onFileSelected: (file: File, previewUrl: string) => void;
  onClear: () => void;
  selectedFile: File | null;
  previewUrl: string | null;
}

function validateFile(file: File): string | null {
  if (!ACCEPTED_TYPES.includes(file.type)) {
    return "Please upload a JPEG or PNG image";
  }
  if (file.size > MAX_SIZE) {
    return "Image must be under 10 MB";
  }
  return null;
}

export function ImageDropzone({
  onFileSelected,
  onClear,
  selectedFile,
  previewUrl,
}: ImageDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    (file: File) => {
      setError(null);

      const validationError = validateFile(file);
      if (validationError) {
        setError(validationError);
        return;
      }

      const objectUrl = URL.createObjectURL(file);
      onFileSelected(file, objectUrl);
    },
    [onFileSelected]
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
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setError(null);
    onClear();
  }, [previewUrl, onClear]);

  if (selectedFile && previewUrl) {
    return (
      <div className="relative">
        <div className="rounded-lg border border-border overflow-hidden">
          <img
            src={previewUrl}
            alt="Selected source image"
            className="w-full h-64 object-contain bg-muted/30"
          />
        </div>
        <div className="absolute top-2 right-2 flex gap-1">
          <Button
            variant="destructive"
            size="icon"
            onClick={handleClear}
            aria-label="Remove selected image"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
        <p className="text-xs text-muted-foreground mt-2">
          {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload source image"
        className={cn(
          "relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors cursor-pointer",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
          isDragging && "border-primary bg-primary/5",
          !isDragging && "border-border hover:border-primary/50"
        )}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
      >
        <div className="flex flex-col items-center gap-3">
          <div className="rounded-full bg-muted/50 p-3">
            <ImageIcon className="w-6 h-6 text-muted-foreground" />
          </div>
          <div className="text-center">
            <p className="text-sm font-medium">
              Drag and drop an image or{" "}
              <span className="text-primary">browse files</span>
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              JPG or PNG, maximum 10MB
            </p>
          </div>
        </div>
        <input
          ref={inputRef}
          id="tryoff-image-input"
          type="file"
          accept="image/jpeg,image/png"
          className="hidden"
          onChange={handleInputChange}
          aria-hidden="true"
        />
      </div>

      {error && (
        <p className="text-sm text-destructive flex items-center gap-1" role="alert">
          <X className="w-3 h-3" />
          {error}
        </p>
      )}
    </div>
  );
}
