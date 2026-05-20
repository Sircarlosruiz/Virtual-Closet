"use client";

import { useState } from "react";
import Link from "next/link";
import { MoreHorizontal } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { PrendaResponse, deletePrenda } from "@/lib/api/prendas";
import { toast } from "sonner";

interface PrendaCardProps {
  prenda: PrendaResponse;
  onDelete?: (id: string) => void;
}

const statusConfig: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  lista: { label: "Lista", variant: "default" },
  procesando: { label: "Procesando", variant: "secondary" },
  pendiente: { label: "Pendiente", variant: "outline" },
  error: { label: "Error", variant: "destructive" },
};

export function PrendaCard({ prenda, onDelete }: PrendaCardProps) {
  const config = statusConfig[prenda.estado] || statusConfig.pendiente;
  const isClickable = prenda.estado === "lista";
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await deletePrenda(prenda.id);
      onDelete?.(prenda.id);
      toast.success("Prenda eliminada");
    } catch {
      toast.error("Error al eliminar la prenda");
    } finally {
      setIsDeleting(false);
      setShowDeleteDialog(false);
    }
  };

  const cardContent = (
    <>
      <div className="relative aspect-square bg-zinc-100 dark:bg-zinc-800 rounded-lg overflow-hidden group">
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
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              className="absolute top-2 left-2 p-1 rounded-full bg-black/40 text-white opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/60"
              aria-label="Opciones"
            >
              <MoreHorizontal className="w-4 h-4" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            <DropdownMenuItem
              className="text-red-600 focus:text-red-600"
              onSelect={() => setShowDeleteDialog(true)}
            >
              Eliminar
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      <p className="mt-2 text-sm font-medium text-zinc-900 dark:text-zinc-50 truncate">
        {prenda.nombre}
      </p>
    </>
  );

  return (
    <>
      {isClickable ? (
        <Link href={`/dashboard/prendas/${prenda.id}`} className="group block">
          {cardContent}
        </Link>
      ) : (
        <div className="block">{cardContent}</div>
      )}

      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Eliminar esta prenda?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción no se puede deshacer.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={isDeleting}
              className="bg-red-600 hover:bg-red-700"
            >
              {isDeleting ? "Eliminando..." : "Eliminar"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
