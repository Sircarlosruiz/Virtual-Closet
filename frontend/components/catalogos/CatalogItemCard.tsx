"use client";

import { useState } from "react";
import { CatalogoItem } from "@/lib/api/catalogos";
import { useRemoveCatalogoItem } from "@/hooks/useCatalogos";
import { Button } from "@/components/ui/button";
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
import { ArrowUp, ArrowDown, Trash2 } from "lucide-react";

interface CatalogItemCardProps {
  item: CatalogoItem;
  catalogId: string;
  isFirst: boolean;
  isLast: boolean;
  onMoveUp: () => void;
  onMoveDown: () => void;
}

export function CatalogItemCard({
  item,
  catalogId,
  isFirst,
  isLast,
  onMoveUp,
  onMoveDown,
}: CatalogItemCardProps) {
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const removeMutation = useRemoveCatalogoItem();

  const handleDelete = () => {
    removeMutation.mutate({ catalogId, itemId: item.id });
    setShowDeleteDialog(false);
  };

  return (
    <>
      <div className="group relative bg-white dark:bg-zinc-900 rounded-lg border overflow-hidden">
        <div className="relative aspect-square bg-zinc-100 dark:bg-zinc-800">
          <img
            src={item.image_url}
            alt={item.garment_name}
            className="w-full h-full object-cover"
          />
        </div>
        <div className="p-3">
          <h4 className="text-sm font-medium truncate">{item.garment_name}</h4>
          <p className="text-sm text-muted-foreground mt-1">${item.price.toFixed(2)}</p>
          <p className="text-xs text-muted-foreground mt-1">SKU: {item.sku}</p>
          <div className="flex items-center justify-between mt-2">
            <div className="flex gap-1">
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                disabled={isFirst}
                onClick={onMoveUp}
              >
                <ArrowUp className="h-3 w-3" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                disabled={isLast}
                onClick={onMoveDown}
              >
                <ArrowDown className="h-3 w-3" />
              </Button>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 text-red-600 hover:text-red-700 opacity-0 group-hover:opacity-100 transition-opacity"
              onClick={() => setShowDeleteDialog(true)}
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          </div>
        </div>
      </div>

      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Eliminar esta prenda del catálogo?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción no se puede deshacer. La prenda seguirá disponible en tu inventario.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={removeMutation.isPending}
              className="bg-red-600 hover:bg-red-700"
            >
              {removeMutation.isPending ? "Eliminando..." : "Eliminar"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
