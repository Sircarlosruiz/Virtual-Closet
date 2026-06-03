"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { PrendaGrid } from "@/components/prendas/PrendaGrid";
import { usePrendas } from "@/hooks/usePrendas";
import { useQueryClient } from "@tanstack/react-query";
import { BookOpen, CheckCircle2, Shirt } from "lucide-react";

export function DashboardContent() {
  const queryClient = useQueryClient();
  const { prendas, isLoading, fetchNextPage, hasNextPage } = usePrendas();

  const handleDelete = (id: string) => {
    queryClient.setQueryData(["prendas"], (prev: any) => ({
      items: (prev?.items || []).filter((p: any) => p.id !== id),
      next_cursor: prev?.next_cursor,
    }));
  };

  const listaCount = prendas.filter((p) => p.estado === "lista").length;

  return (
    <>
      {/* Stats strip */}
      <div
        className="rounded-2xl p-5 text-white mb-6 overflow-hidden relative"
        style={{
          background: "linear-gradient(135deg,#4F46E5 0%,#6366F1 55%,#8B5CF6 100%)",
          boxShadow: "0 10px 26px rgba(79,70,229,.3)",
        }}
      >
        <div className="flex items-start justify-between">
          <div>
            <div className="text-xs font-semibold opacity-85 mb-1">Prendas en tu clóset</div>
            <div className="text-4xl font-extrabold tracking-tight leading-none">
              {prendas.length}
            </div>
            <div className="text-xs font-semibold mt-1" style={{ color: "#C7F9E5" }}>
              ▲ +6 este mes
            </div>
          </div>
          {/* Sparkline placeholder */}
          <svg width={150} height={44} viewBox="0 0 150 44" className="opacity-80">
            <path d="M0 38 L18 30 L36 32 L54 18 L72 22 L90 10 L108 6 L150 2" fill="none" stroke="rgba(255,255,255,.9)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
            <circle cx={150} cy={2} r={3.5} fill="#fff" />
          </svg>
        </div>
        <div className="flex gap-2 mt-4">
          <span
            className="flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold"
            style={{ background: "rgba(255,255,255,.16)" }}
          >
            <BookOpen className="w-3 h-3" /> 2 catálogos
          </span>
          <span
            className="flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold"
            style={{ background: "rgba(255,255,255,.16)" }}
          >
            <CheckCircle2 className="w-3 h-3" /> {listaCount} listas
          </span>
        </div>
      </div>

      {/* Extraction shortcut */}
      <Link href="/extraction/new">
        <div className="rounded-xl border bg-card p-4 mb-6 hover:shadow-md transition-shadow cursor-pointer group">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Shirt className="w-5 h-5" />
            </div>
            <div className="flex-1">
              <div className="text-sm font-semibold group-hover:text-primary transition-colors">
                Extraer prendas
              </div>
              <div className="text-xs text-muted-foreground">
                Extrae prendas de tus imágenes para usarlas en VTON
              </div>
            </div>
            <svg className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
            </svg>
          </div>
        </div>
      </Link>

      {/* Garment header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Mis prendas</h2>
        <Link href="/dashboard/media/extracted">
          <Button variant="outline" size="sm" className="gap-2">
            Prendas extraídas
          </Button>
        </Link>
      </div>

      <PrendaGrid prendas={prendas} isLoading={isLoading} onDelete={handleDelete} />

      {hasNextPage && (
        <div className="mt-6 flex justify-center">
          <Button variant="outline" onClick={() => fetchNextPage()}>
            Cargar más
          </Button>
        </div>
      )}
    </>
  );
}
