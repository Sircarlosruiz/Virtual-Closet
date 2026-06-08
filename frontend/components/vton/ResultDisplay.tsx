"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, ArrowLeft, Loader2 } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface ResultDisplayProps {
  garmentUrl: string | null;
  resultUrl: string | null;
  errorReason: string | null;
  jobId: string;
}

export function ResultDisplay({
  garmentUrl,
  resultUrl,
  errorReason,
  jobId,
}: ResultDisplayProps) {
  const router = useRouter();
  const [resultLoading, setResultLoading] = useState(true);

  // Failed state
  if (errorReason) {
    return (
      <div className="space-y-4">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Generación fallida</AlertTitle>
          <AlertDescription>
            {errorReason}
          </AlertDescription>
        </Alert>

        <Button
          variant="outline"
          onClick={() => router.push("/generate")}
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Intentar de nuevo
        </Button>
      </div>
    );
  }

  // Still loading result URL
  if (!resultUrl) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-64 w-full rounded-lg" />
        <div className="flex justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Resultado</h2>
        <Button
          variant="outline"
          size="sm"
          onClick={() => router.push("/generate")}
        >
          Generar otra
        </Button>
      </div>

      {/* Before/After Comparison */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {/* Before: Garment */}
        <div className="space-y-2">
          <p className="text-sm font-medium text-muted-foreground">Prenda original</p>
          <div className="rounded-lg border border-border overflow-hidden bg-muted/30">
            {garmentUrl ? (
              <img
                src={garmentUrl}
                alt="Prenda original"
                className="w-full h-auto object-contain"
              />
            ) : (
              <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
                Imagen no disponible
              </div>
            )}
          </div>
        </div>

        {/* After: Result */}
        <div className="space-y-2">
          <p className="text-sm font-medium text-muted-foreground">Resultado</p>
          <div className="rounded-lg border border-border overflow-hidden bg-muted/30 relative">
            {resultLoading && (
              <div className="absolute inset-0 flex items-center justify-center bg-muted/50">
                <Loader2 className="w-6 h-6 animate-spin" />
              </div>
            )}
            <img
              src={resultUrl}
              alt="Resultado de prueba virtual"
              className={cn(
                "w-full h-auto object-contain transition-opacity",
                resultLoading ? "opacity-0" : "opacity-100"
              )}
              onLoad={() => setResultLoading(false)}
            />
          </div>
        </div>
      </div>

      {/* Job reference */}
      <p className="text-xs text-muted-foreground text-center">
        ID del trabajo: {jobId}
      </p>
    </div>
  );
}
