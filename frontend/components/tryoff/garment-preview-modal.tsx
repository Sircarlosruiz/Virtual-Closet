"use client";

import { ArrowUpRight, Download, AlertCircle, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const GARMENT_LABELS: Record<string, string> = {
  upper: "Upper Garment",
  lower: "Lower Garment",
  dress: "Full Dress",
};

interface GarmentPreviewModalProps {
  imageUrl: string;
  garmentType: string;
  mediaId: string;
  jobId: string;
  filename?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function GarmentPreviewModal({
  imageUrl,
  garmentType,
  mediaId,
  jobId,
  filename,
  open,
  onOpenChange,
}: GarmentPreviewModalProps) {
  const router = useRouter();
  const [imageError, setImageError] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);

  const handleUseInVton = () => {
    onOpenChange(false);
    router.push(`/dashboard/generate?garment_id=${mediaId}`);
  };

  const handleDownload = async () => {
    setIsDownloading(true);
    try {
      const response = await fetch(imageUrl);
      if (!response.ok) {
        throw new Error("Download failed");
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename ?? `extracted-${garmentType}-${jobId}.png`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch {
      toast.error("No se pudo descargar la imagen");
    } finally {
      setIsDownloading(false);
    }
  };

  const handleImageError = () => {
    setImageError(true);
    toast.error("La imagen ya no está disponible");
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      setImageError(false);
    }
    onOpenChange(newOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-3xl sm:max-w-4xl">
        {imageError ? (
          <div className="flex flex-col items-center justify-center py-12 text-center gap-4">
            <AlertCircle className="w-12 h-12 text-muted-foreground" />
            <div>
              <DialogHeader>
                <DialogTitle>Image no longer available</DialogTitle>
                <DialogDescription>
                  The extracted garment image has been removed or the link has expired.
                </DialogDescription>
              </DialogHeader>
            </div>
          </div>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>
                {GARMENT_LABELS[garmentType] ?? garmentType}
              </DialogTitle>
              <DialogDescription>
                Extracted garment — full-size preview
              </DialogDescription>
            </DialogHeader>

            <div className="flex justify-center bg-zinc-50 dark:bg-zinc-900 rounded-lg p-4">
              <img
                src={imageUrl}
                alt={GARMENT_LABELS[garmentType] ?? garmentType}
                className="max-h-[70vh] w-auto object-contain rounded"
                onError={handleImageError}
              />
            </div>

            <div className="flex items-center gap-2">
              <Badge variant="secondary">
                {GARMENT_LABELS[garmentType] ?? garmentType}
              </Badge>
            </div>

            <div className="flex gap-2">
              <Button
                variant="secondary"
                className="flex-1 gap-2"
                onClick={handleUseInVton}
              >
                Use in VTON
                <ArrowUpRight className="w-4 h-4" />
              </Button>
              <Button
                variant="outline"
                className="flex-1 gap-2"
                onClick={handleDownload}
                disabled={isDownloading}
              >
                {isDownloading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Download className="w-4 h-4" />
                )}
                Download
              </Button>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
