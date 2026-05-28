"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, ArrowRight, Clock, Loader2, PlayCircle, CheckCircle2, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

type JobStatus = "queued" | "processing" | "completed" | "failed";
type ClothType = "upper_body" | "lower_body" | "dress";

interface HistoryItem {
  job_id: string;
  status: JobStatus;
  cloth_type: ClothType;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  result_url: string | null;
  error_reason: string | null;
  retry_count: number;
}

const CLOTH_TYPE_LABELS: Record<ClothType, string> = {
  upper_body: "Parte Superior",
  lower_body: "Parte Inferior",
  dress: "Vestido",
};

const STATUS_BADGE_CONFIG: Record<JobStatus, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  queued: { label: "En cola", variant: "secondary" },
  processing: { label: "Procesando", variant: "outline" },
  completed: { label: "Completado", variant: "default" },
  failed: { label: "Fallido", variant: "destructive" },
};

const STATUS_ICON: Record<JobStatus, React.ReactNode> = {
  queued: <Clock className="w-3 h-3" />,
  processing: <PlayCircle className="w-3 h-3 animate-pulse" />,
  completed: <CheckCircle2 className="w-3 h-3" />,
  failed: <XCircle className="w-3 h-3" />,
};

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("es-NI", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function JobRow({ item }: { item: HistoryItem }) {
  const router = useRouter();
  const statusConfig = STATUS_BADGE_CONFIG[item.status];

  return (
    <button
      type="button"
      onClick={() => router.push(`/dashboard/jobs/${item.job_id}`)}
      className={cn(
        "flex items-center gap-3 w-full p-3 rounded-lg border border-border",
        "hover:bg-muted/50 transition-colors text-left",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
      )}
      aria-label={`Ver trabajo ${item.cloth_type} - ${statusConfig.label}`}
    >
      {/* Thumbnail */}
      <div className="shrink-0 w-12 h-12 rounded-md overflow-hidden bg-muted/30 border border-border">
        {item.status === "completed" && item.result_url ? (
          <img
            src={item.result_url}
            alt="Resultado"
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-muted-foreground">
            {STATUS_ICON[item.status]}
          </div>
        )}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <Badge variant={statusConfig.variant} className="text-xs">
            {statusConfig.label}
          </Badge>
          <span className="text-xs text-muted-foreground">
            {CLOTH_TYPE_LABELS[item.cloth_type]}
          </span>
        </div>
        <p className="text-xs text-muted-foreground mt-0.5">
          {formatDate(item.created_at)}
        </p>
      </div>

      <ArrowRight className="w-4 h-4 text-muted-foreground shrink-0" />
    </button>
  );
}

export function JobHistoryList() {
  const router = useRouter();
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchJobs = useCallback(
    async (pageNum: number, append = false) => {
      try {
        setError(null);
        const data = await apiFetch(
          `/api/vton/jobs?page=${pageNum}&page_size=20`
        );

        const newItems = Array.isArray(data.items) ? data.items : [];
        const newTotal = data.total ?? 0;

        setItems(append ? [...items, ...newItems] : newItems);
        setTotal(newTotal);
        setPage(pageNum);
      } catch {
        setError("Error al cargar el historial");
      }
    },
    [items]
  );

  const loadMore = useCallback(() => {
    setLoadingMore(true);
    fetchJobs(page + 1, true).finally(() => setLoadingMore(false));
  }, [page, fetchJobs]);

  // Initial load
  const [initialLoaded, setInitialLoaded] = useState(false);
  if (!initialLoaded) {
    setInitialLoaded(true);
    fetchJobs(1).finally(() => setLoading(false));
  }

  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  if (error && items.length === 0) {
    return (
      <div className="text-center py-8">
        <AlertCircle className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
        <p className="text-sm text-muted-foreground">{error}</p>
        <Button
          variant="outline"
          size="sm"
          className="mt-3"
          onClick={() => {
            setLoading(true);
            fetchJobs(1).finally(() => setLoading(false));
          }}
        >
          Reintentar
        </Button>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-12 space-y-4">
        <div className="w-12 h-12 rounded-full bg-muted/50 flex items-center justify-center mx-auto">
          <Clock className="w-6 h-6 text-muted-foreground" />
        </div>
        <div>
          <p className="font-medium">Aún no tienes generaciones</p>
          <p className="text-sm text-muted-foreground mt-1">
            Crea tu primera prueba virtual con IA
          </p>
        </div>
        <Button onClick={() => router.push("/dashboard/generate")}>
          Generar tu primera prueba
        </Button>
      </div>
    );
  }

  const hasMore = items.length < total;

  return (
    <div className="space-y-3">
      {items.map((item) => (
        <JobRow key={item.job_id} item={item} />
      ))}

      {hasMore && (
        <div className="flex justify-center pt-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadMore}
            disabled={loadingMore}
          >
            {loadingMore ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Cargando...
              </>
            ) : (
              "Cargar más"
            )}
          </Button>
        </div>
      )}
    </div>
  );
}
