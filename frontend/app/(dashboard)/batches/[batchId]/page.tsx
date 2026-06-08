"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  ArrowLeft,
  CheckCircle2,
  Clock,
  Loader2,
  XCircle,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { BatchItemRow } from "@/components/batch/BatchItemRow";
import { getBatch, retryBatchItem } from "@/lib/api/batches";
import type { BatchDetailResponse, BatchItemResponse } from "@/lib/api/batches";

const TERMINAL_STATUSES = ["complete", "partial", "failed"];

const STATUS_BANNER: Record<
  string,
  { label: string; color: string; bg: string }
> = {
  complete: {
    label: "Lote Completado",
    color: "text-green-700",
    bg: "bg-green-50 border-green-200",
  },
  partial: {
    label: "Lote Parcialmente Completado",
    color: "text-orange-700",
    bg: "bg-orange-50 border-orange-200",
  },
  failed: {
    label: "Lote Fallido",
    color: "text-destructive",
    bg: "bg-destructive/10 border-destructive/20",
  },
};

export default function BatchProgressPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const batchId = params.batchId as string;

  const [retryingItemId, setRetryingItemId] = useState<string | null>(null);
  const [retryError, setRetryError] = useState<string | null>(null);

  const { data, isLoading, error, refetch } = useQuery<BatchDetailResponse>({
    queryKey: ["batch", batchId],
    queryFn: () => getBatch(batchId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status && TERMINAL_STATUSES.includes(status)) {
        return false;
      }
      return 3000;
    },
    retry: false,
  });

  const retryMutation = useMutation({
    mutationFn: ({ itemId }: { itemId: string }) =>
      retryBatchItem(batchId, itemId),
    onMutate: async ({ itemId }) => {
      // Optimistic update
      setRetryingItemId(itemId);
      setRetryError(null);

      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ["batch", batchId] });

      // Snapshot previous value
      const previous = queryClient.getQueryData<BatchDetailResponse>([
        "batch",
        batchId,
      ]);

      // Optimistically update
      if (previous) {
        queryClient.setQueryData<BatchDetailResponse>(
          ["batch", batchId],
          {
            ...previous,
            items: previous.items.map((item) =>
              item.id === itemId
                ? { ...item, status: "pending" as const, error_message: null }
                : item
            ),
          }
        );
      }

      return { previous };
    },
    onError: (err: Error, _variables, context) => {
      // Revert optimistic update
      if (context?.previous) {
        queryClient.setQueryData(["batch", batchId], context.previous);
      }
      setRetryError(err.message || "Error al reintentar");
      toast.error("No se pudo reintentar el elemento");
    },
    onSettled: () => {
      setRetryingItemId(null);
      // Refetch to get latest state
      queryClient.invalidateQueries({ queryKey: ["batch", batchId] });
    },
  });

  const handleRetry = useCallback(
    (itemId: string) => {
      retryMutation.mutate({ itemId });
    },
    [retryMutation]
  );

  const prevStatusRef = useRef<string | null>(null);

  useEffect(() => {
    if (data?.status && data.status !== prevStatusRef.current) {
      prevStatusRef.current = data.status;
      if (TERMINAL_STATUSES.includes(data.status)) {
        toast.info(
          data.status === "complete"
            ? "Lote completado exitosamente"
            : data.status === "partial"
              ? "Algunos elementos fallaron"
              : "Lote fallido"
        );
      }
    }
  }, [data?.status]);

  if (isLoading && !data) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        <div className="h-8 w-48 bg-muted rounded animate-pulse" />
        <div className="h-32 bg-muted rounded animate-pulse" />
        <div className="space-y-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-20 bg-muted rounded animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive">
              No se pudo cargar el lote.{" "}
              <Button
                variant="link"
                className="p-0"
                onClick={() => refetch()}
              >
                Reintentar
              </Button>
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!data) return null;

  const isTerminal = TERMINAL_STATUSES.includes(data.status);
  const banner = STATUS_BANNER[data.status];
  const progressPercent =
    data.total_items > 0
      ? Math.round((data.completed_count / data.total_items) * 100)
      : 0;

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.push("/batches")}
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          Volver
        </Button>
        <div>
          <h1 className="text-2xl font-semibold">{data.name}</h1>
          <p className="text-sm text-muted-foreground">
            {data.total_items} elementos · Creado{" "}
            {new Date(data.created_at).toLocaleDateString()}
          </p>
        </div>
      </div>

      {/* Progress */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Progreso del Lote</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between text-sm">
            <span>
              {data.completed_count} / {data.total_items} completados
            </span>
            <span className="font-medium">{progressPercent}%</span>
          </div>
          <Progress value={progressPercent} className="h-2" />

          <div className="flex gap-6 text-sm">
            <span className="flex items-center gap-1 text-green-600">
              <CheckCircle2 className="w-4 h-4" />
              {data.completed_count} completados
            </span>
            <span className="flex items-center gap-1 text-blue-500">
              <Loader2 className="w-4 h-4 animate-spin" />
              {data.total_items - data.completed_count - data.failed_count} en
              progreso
            </span>
            <span className="flex items-center gap-1 text-destructive">
              <XCircle className="w-4 h-4" />
              {data.failed_count} fallidos
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Terminal banner */}
      {isTerminal && banner && (
        <div
          className={`rounded-lg border p-4 ${banner.bg} ${banner.color}`}
        >
          <p className="font-medium">{banner.label}</p>
          {data.status === "partial" && (
            <p className="text-sm mt-1">
              {data.completed_count} completados,{" "}
              {data.failed_count} fallidos. Puedes reintentar los elementos
              fallidos.
            </p>
          )}
        </div>
      )}

      {/* Item list */}
      <Separator />
      <div className="space-y-3">
        {data.items.map((item) => (
          <BatchItemRow
            key={item.id}
            item={item}
            onRetry={
              item.status === "failed" && retryingItemId !== item.id
                ? () => handleRetry(item.id)
                : undefined
            }
            isRetrying={retryingItemId === item.id}
            retryError={
              retryingItemId === item.id ? null : retryError
            }
          />
        ))}
      </div>
    </div>
  );
}
