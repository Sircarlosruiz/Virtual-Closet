"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CheckCircle2, Clock3, Loader2, RefreshCw, Sparkles, XCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { retryBatchItem } from "@/lib/api/batches";
import { getPoseSet, type PoseSetDetail, type PoseSetItem } from "@/lib/api/pose-sets";
import { cn } from "@/lib/utils";

const TERMINAL = new Set(["complete", "failed"]);
const POSE_LABELS: Record<string, string> = { front: "Frente", side: "Perfil", back: "Espalda" };

function StatusIcon({ status }: { status: PoseSetItem["status"] }) {
  if (status === "complete") return <CheckCircle2 className="h-5 w-5 text-emerald-600" />;
  if (status === "failed") return <XCircle className="h-5 w-5 text-destructive" />;
  if (status === "processing") return <Loader2 className="h-5 w-5 animate-spin text-primary" />;
  return <Clock3 className="h-5 w-5 text-muted-foreground" />;
}

function statusLabel(status: PoseSetItem["status"]) {
  return { complete: "Completada", failed: "Fallida", processing: "Procesando", pending: "En cola" }[status];
}

export function PoseSetResultView({ poseSetId }: { poseSetId: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const query = useQuery<PoseSetDetail>({
    queryKey: ["pose-set", poseSetId],
    queryFn: () => getPoseSet(poseSetId),
    retry: false,
    refetchInterval: (current) => {
      const items = current.state.data?.items;
      if (items?.length && items.every((item) => TERMINAL.has(item.status))) return false;
      return 3000;
    },
  });

  const retryMutation = useMutation({
    mutationFn: (itemId: string) => retryBatchItem(query.data!.batch_id, itemId),
    onSuccess: () => {
      toast.success("Pose enviada nuevamente");
      void queryClient.invalidateQueries({ queryKey: ["pose-set", poseSetId] });
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "No se pudo reintentar la pose"),
  });

  if (query.isLoading && !query.data) return <LoadingState />;
  if (query.error && !query.data) {
    const notFound = query.error instanceof Error && query.error.message === "HTTP 404";
    return <div className="mx-auto max-w-4xl px-4 py-10"><Card className="border-destructive/30"><CardContent className="space-y-4 p-8 text-center"><XCircle className="mx-auto h-10 w-10 text-destructive" /><h1 className="text-xl font-semibold">{notFound ? "Set de poses no encontrado" : "No pudimos cargar este resultado"}</h1><p className="text-sm text-muted-foreground">{notFound ? "Puede que no exista o no tengas acceso a este envío." : "Revisa tu conexión e inténtalo de nuevo."}</p><Button onClick={() => void query.refetch()}>Reintentar</Button></CardContent></Card></div>;
  }
  if (!query.data) return null;

  const data = query.data;
  const reconnecting = Boolean(query.error);
  const completeCount = data.items.filter((item) => item.status === "complete").length;
  const terminal = data.items.length > 0 && data.items.every((item) => TERMINAL.has(item.status));

  return <main className="mx-auto max-w-6xl px-4 py-8"><div className="mb-8 flex items-start justify-between gap-4"><div><Button variant="ghost" size="sm" className="mb-4 -ml-3" onClick={() => router.push("/generate")}><ArrowLeft className="mr-1 h-4 w-4" />Volver a generar</Button><p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary">Estudio de poses</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">Tu set está tomando forma</h1><p className="mt-2 text-sm text-muted-foreground">{completeCount} de {data.items.length} ángulos listos</p></div><Sparkles className="hidden h-9 w-9 text-primary/60 sm:block" /></div>{reconnecting && <div className="mb-5 flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800"><RefreshCw className="h-4 w-4" />Reconectando… mostramos el último estado conocido.</div>}{terminal && <div className="mb-5 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">Todos los ángulos tienen un resultado final.</div>}<div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{data.items.map((item) => <Card key={item.batch_item_id} className={cn("overflow-hidden", item.status === "complete" && "border-emerald-200", item.status === "failed" && "border-destructive/30")}><div className="aspect-[4/5] bg-muted">{item.image_url ? <img src={item.image_url} alt={POSE_LABELS[item.pose_type ?? ""] ?? "Resultado de pose"} className="h-full w-full object-cover" /> : <div className="flex h-full flex-col items-center justify-center gap-3 text-center text-muted-foreground"><StatusIcon status={item.status} /><span className="text-sm">{item.status === "processing" ? "Generando imagen…" : item.status === "pending" ? "En cola…" : "Sin imagen"}</span></div>}</div><CardHeader className="pb-2"><div className="flex items-center justify-between"><CardTitle className="text-lg">{POSE_LABELS[item.pose_type ?? ""] ?? "Pose"}</CardTitle><StatusIcon status={item.status} /></div><Badge variant="outline" className="w-fit">{statusLabel(item.status)}</Badge></CardHeader><CardContent className="space-y-3">{item.error_message && <p className="text-sm text-destructive">{item.error_message}</p>}{item.status === "failed" && <Button className="w-full" variant="outline" disabled={retryMutation.isPending} onClick={() => retryMutation.mutate(item.batch_item_id)}><RefreshCw className="mr-2 h-4 w-4" />{retryMutation.isPending ? "Reintentando…" : "Reintentar pose"}</Button>}</CardContent></Card>)}</div></main>;
}

function LoadingState() {
  return <div className="mx-auto max-w-6xl space-y-6 px-4 py-8"><div className="h-10 w-72 animate-pulse rounded bg-muted" /><div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{[1, 2, 3].map((item) => <div key={item} className="aspect-[4/5] animate-pulse rounded-xl bg-muted" />)}</div></div>;
}
