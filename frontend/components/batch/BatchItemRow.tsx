"use client";

import { CheckCircle2, Clock, Loader2, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { BatchItemResponse } from "@/lib/api/batches";

const STATUS_CONFIG: Record<
  string,
  { label: string; color: string; icon: React.ReactNode }
> = {
  pending: {
    label: "Pendiente",
    color: "text-muted-foreground",
    icon: <Clock className="w-4 h-4" />,
  },
  processing: {
    label: "Procesando",
    color: "text-blue-500",
    icon: <Loader2 className="w-4 h-4 animate-spin" />,
  },
  complete: {
    label: "Completado",
    color: "text-green-500",
    icon: <CheckCircle2 className="w-4 h-4" />,
  },
  failed: {
    label: "Fallido",
    color: "text-destructive",
    icon: <XCircle className="w-4 h-4" />,
  },
};

interface BatchItemRowProps {
  item: BatchItemResponse;
  garmentUrl?: string;
  modelUrl?: string;
  onRetry?: () => void;
  isRetrying?: boolean;
  retryError?: string | null;
}

export function BatchItemRow({
  item,
  garmentUrl,
  modelUrl,
  onRetry,
  isRetrying = false,
  retryError = null,
}: BatchItemRowProps) {
  const displayStatus = isRetrying ? "processing" : item.status;
  const config = STATUS_CONFIG[displayStatus] ?? STATUS_CONFIG.pending;

  return (
    <div className="flex items-start gap-4 rounded-lg border p-4">
      {/* Garment thumbnail */}
      <div className="shrink-0">
        {garmentUrl ? (
          <img
            src={garmentUrl}
            alt="Garment"
            className="h-16 w-16 rounded-md object-cover"
          />
        ) : (
          <div className="h-16 w-16 rounded-md bg-muted" />
        )}
      </div>

      {/* Arrow */}
      <div className="flex items-center pt-6 text-muted-foreground">
        <span className="text-sm">→</span>
      </div>

      {/* Model thumbnail */}
      <div className="shrink-0">
        {modelUrl ? (
          <img
            src={modelUrl}
            alt="Model"
            className="h-16 w-16 rounded-md object-cover"
          />
        ) : (
          <div className="h-16 w-16 rounded-md bg-muted" />
        )}
      </div>

      {/* Info */}
      <div className="flex-1 space-y-1">
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-xs">
            {item.cloth_type.replace("_", " ")}
          </Badge>
          <span className={cn("flex items-center gap-1 text-sm", config.color)}>
            {config.icon}
            {config.label}
          </span>
        </div>

        {item.status === "failed" && item.error_message && !isRetrying && (
          <p className="text-xs text-destructive line-clamp-2">
            {item.error_message}
          </p>
        )}

        {retryError && (
          <p className="text-xs text-destructive">{retryError}</p>
        )}

        {item.retry_count > 0 && !isRetrying && (
          <p className="text-xs text-muted-foreground">
            Reintento #{item.retry_count}
          </p>
        )}
      </div>

      {/* Retry button */}
      {onRetry && item.status === "failed" && !isRetrying && (
        <Button
          variant="outline"
          size="sm"
          onClick={onRetry}
          className="shrink-0"
        >
          Reintentar
        </Button>
      )}

      {isRetrying && (
        <div className="shrink-0 flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span>Reintentando...</span>
        </div>
      )}
    </div>
  );
}
