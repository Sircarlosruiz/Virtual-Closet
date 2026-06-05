"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { listBatches } from "@/lib/api/batches";
import type { BatchListItem } from "@/lib/api/batches";

const STATUS_CONFIG: Record<
  string,
  { label: string; variant: "default" | "secondary" | "destructive" | "outline" }
> = {
  complete: { label: "Completado", variant: "default" },
  partial: { label: "Parcial", variant: "secondary" },
  failed: { label: "Fallido", variant: "destructive" },
  "in-progress": { label: "En progreso", variant: "outline" },
  pending: { label: "Pendiente", variant: "outline" },
};

export default function BatchHistoryPage() {
  const router = useRouter();

  const { data, isLoading, error } = useQuery({
    queryKey: ["batches", 1],
    queryFn: () => listBatches(1, 20),
  });

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        <div className="h-8 w-48 bg-muted rounded animate-pulse" />
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-16 bg-muted rounded animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-6">
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive">
              No se pudieron cargar los lotes. Por favor intenta de nuevo.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const batches = data?.items ?? [];
  const total = data?.total ?? 0;

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Historial de Lotes</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {total} {total === 1 ? "lote" : "lotes"} en total
          </p>
        </div>
        <Button onClick={() => router.push("/dashboard/batches/new")}>
          <Plus className="w-4 h-4 mr-2" />
          Nuevo Lote
        </Button>
      </div>

      {/* Empty state */}
      {batches.length === 0 && (
        <Card>
          <CardContent className="pt-6 pb-6 text-center">
            <p className="text-muted-foreground mb-4">
              No tienes lotes aún. Crea tu primer lote para comenzar.
            </p>
            <Button onClick={() => router.push("/dashboard/batches/new")}>
              <Plus className="w-4 h-4 mr-2" />
              Crear tu primer lote
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Batch list */}
      {batches.length > 0 && (
        <div className="space-y-3">
          {batches.map((batch) => (
            <BatchRow key={batch.id} batch={batch} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {total > 20 && (
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>
            Mostrando 1–{Math.min(20, total)} de {total}
          </span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled>
              Anterior
            </Button>
            <Button variant="outline" size="sm">
              Siguiente
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function BatchRow({ batch }: { batch: BatchListItem }) {
  const router = useRouter();
  const statusConfig = STATUS_CONFIG[batch.status] ?? STATUS_CONFIG.pending;

  return (
    <Card
      className="cursor-pointer hover:bg-accent/50 transition-colors"
      onClick={() => router.push(`/dashboard/batches/${batch.id}`)}
    >
      <CardContent className="pt-4 pb-4">
        <div className="flex items-center justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-medium truncate">{batch.name}</h3>
              <Badge variant={statusConfig.variant}>
                {statusConfig.label}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              {new Date(batch.created_at).toLocaleDateString()} ·{" "}
              {batch.total_items} elementos
            </p>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <span className="text-green-600">
              {batch.completed_count} ✓
            </span>
            <span className="text-destructive">
              {batch.failed_count} ✗
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
