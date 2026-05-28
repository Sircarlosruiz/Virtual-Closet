"use client";

import { useRef, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Loader2, AlertCircle, CheckCircle2, Clock, PlayCircle, XCircle } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

type JobStatus = "queued" | "processing" | "completed" | "failed";

interface JobData {
  job_id: string;
  status: JobStatus;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  result_url: string | null;
  error_reason: string | null;
  retry_count: number;
}

const STATUS_CONFIG: Record<JobStatus, { label: string; color: string; icon: React.ReactNode }> = {
  queued: {
    label: "En cola",
    color: "text-muted-foreground",
    icon: <Clock className="w-5 h-5" />,
  },
  processing: {
    label: "Procesando",
    color: "text-blue-500",
    icon: <PlayCircle className="w-5 h-5 animate-pulse" />,
  },
  completed: {
    label: "Completado",
    color: "text-green-500",
    icon: <CheckCircle2 className="w-5 h-5" />,
  },
  failed: {
    label: "Fallido",
    color: "text-destructive",
    icon: <XCircle className="w-5 h-5" />,
  },
};

function StatusIndicator({ status }: { status: JobStatus }) {
  const config = STATUS_CONFIG[status];
  return (
    <div className="flex items-center gap-3">
      <span className={cn("shrink-0", config.color)}>{config.icon}</span>
      <div>
        <p className={cn("font-medium", config.color)}>{config.label}</p>
        <p className="text-xs text-muted-foreground">
          {status === "queued" && "Tu generación está en cola de procesamiento"}
          {status === "processing" && "Generando tu prueba virtual..."}
        </p>
      </div>
    </div>
  );
}

function useJobPolling(jobId: string) {
  const { data, isLoading, error, refetch } = useQuery<JobData>({
    queryKey: ["vton-job", jobId],
    queryFn: () => apiFetch(`/api/vton/jobs/${jobId}`),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "completed" || status === "failed") {
        return false;
      }
      return 5000;
    },
    retry: false,
  });

  return { data, isLoading, error, refetch };
}

export function JobStatusPoller({
  jobId,
  onStatusChange,
}: {
  jobId: string;
  onStatusChange?: (status: JobStatus) => void;
}) {
  const { data, isLoading, error, refetch } = useJobPolling(jobId);
  const prevStatusRef = useRef<JobStatus | null>(null);

  useEffect(() => {
    if (data?.status && data.status !== prevStatusRef.current) {
      prevStatusRef.current = data.status;
      onStatusChange?.(data.status);
    }
  }, [data?.status, onStatusChange]);

  if (isLoading && !data) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-24 w-full rounded-lg" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>
          No se pudo cargar el estado del trabajo.
          <Button
            variant="outline"
            size="sm"
            className="mt-2"
            onClick={() => refetch()}
          >
            Reintentar
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  if (!data) return null;

  const { status, error_reason } = data;
  const isTerminal = status === "completed" || status === "failed";

  return (
    <div className="space-y-4">
      <StatusIndicator status={status} />

      {!isTerminal && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span>Suele tomar entre 30 y 120 segundos</span>
        </div>
      )}

      {status === "failed" && (
        <Alert variant="destructive">
          <XCircle className="h-4 w-4" />
          <AlertTitle>Generación fallida</AlertTitle>
          <AlertDescription>
            {error_reason ?? "Ocurrió un error inesperado. Por favor intenta de nuevo."}
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}

export type { JobData, JobStatus };
export { useJobPolling };
