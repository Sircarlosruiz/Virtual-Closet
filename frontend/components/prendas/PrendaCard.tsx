"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { PrendaResponse } from "@/lib/api/prendas";

interface PrendaCardProps {
  prenda: PrendaResponse;
}

const statusConfig: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  lista: { label: "Lista", variant: "default" },
  procesando: { label: "Procesando", variant: "secondary" },
  pendiente: { label: "Pendiente", variant: "outline" },
  error: { label: "Error", variant: "destructive" },
};

export function PrendaCard({ prenda }: PrendaCardProps) {
  const config = statusConfig[prenda.estado] || statusConfig.pendiente;
  const isClickable = prenda.estado === "lista";

  const cardContent = (
    <>
      <div className="relative aspect-square bg-zinc-100 dark:bg-zinc-800 rounded-lg overflow-hidden">
        <img
          src={prenda.imagen_original_url}
          alt={prenda.nombre}
          className="w-full h-full object-cover"
        />
        {prenda.estado === "procesando" && (
          <div className="absolute inset-0 bg-black/30 flex items-center justify-center">
            <div className="w-8 h-8 border-2 border-white border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        {prenda.estado === "error" && (
          <div className="absolute inset-0 bg-black/50" />
        )}
        <Badge
          variant={config.variant}
          className="absolute top-2 right-2"
        >
          {config.label}
        </Badge>
      </div>
      <p className="mt-2 text-sm font-medium text-zinc-900 dark:text-zinc-50 truncate">
        {prenda.nombre}
      </p>
    </>
  );

  if (isClickable) {
    return (
      <Link
        href={`/dashboard/prendas/${prenda.id}`}
        className="group block"
      >
        {cardContent}
      </Link>
    );
  }

  return <div className="block">{cardContent}</div>;
}
