"use client";

import { useState, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { useCatalogo, useUpdateCatalogo, useDeleteCatalogo, useReorderCatalogoItems } from "@/hooks/useCatalogos";
import { CatalogItemCard } from "@/components/catalogos/CatalogItemCard";
import { AddItemPicker } from "@/components/catalogos/AddItemPicker";
import { ConfirmDialog } from "@/components/catalogos/ConfirmDialog";
import { StatusBadge } from "@/components/catalogos/StatusBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ArrowLeft, Plus, Edit2, Check, X, Trash2 } from "lucide-react";

export default function CatalogoDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [showAddPicker, setShowAddPicker] = useState(false);
  const [isEditingName, setIsEditingName] = useState(false);
  const [editName, setEditName] = useState("");
  const [showPublishDialog, setShowPublishDialog] = useState(false);
  const [showUnpublishDialog, setShowUnpublishDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const { data: catalogo, isLoading, error } = useCatalogo(id);
  const updateMutation = useUpdateCatalogo();
  const deleteMutation = useDeleteCatalogo();
  const reorderMutation = useReorderCatalogoItems();

  const items = useMemo(() => {
    if (!catalogo?.items) return [];
    return [...catalogo.items].sort((a, b) => a.position - b.position);
  }, [catalogo?.items]);

  const handleStartEditName = () => {
    setEditName(catalogo?.name ?? "");
    setIsEditingName(true);
  };

  const handleSaveName = () => {
    if (editName.trim() && editName !== catalogo?.name) {
      updateMutation.mutate({ id, input: { name: editName.trim() } });
    }
    setIsEditingName(false);
  };

  const handleCancelEditName = () => {
    setIsEditingName(false);
  };

  const handlePublish = () => {
    updateMutation.mutate({ id, input: { status: "published" } });
    setShowPublishDialog(false);
  };

  const handleUnpublish = () => {
    updateMutation.mutate({ id, input: { status: "draft" } });
    setShowUnpublishDialog(false);
  };

  const handleDelete = () => {
    deleteMutation.mutate(id, {
      onSuccess: () => router.push("/dashboard/catalogos"),
    });
    setShowDeleteDialog(false);
  };

  const handleMoveUp = (itemId: string) => {
    const idx = items.findIndex((i) => i.id === itemId);
    if (idx <= 0) return;
    const newItems = [...items];
    [newItems[idx - 1], newItems[idx]] = [newItems[idx], newItems[idx - 1]];
    submitReorder(newItems);
  };

  const handleMoveDown = (itemId: string) => {
    const idx = items.findIndex((i) => i.id === itemId);
    if (idx < 0 || idx >= items.length - 1) return;
    const newItems = [...items];
    [newItems[idx], newItems[idx + 1]] = [newItems[idx + 1], newItems[idx]];
    submitReorder(newItems);
  };

  const submitReorder = (newItems: typeof items) => {
    reorderMutation.mutate({
      catalogId: id,
      input: { ordered_item_ids: newItems.map((i) => i.id) },
    });
  };

  if (isLoading) {
    return (
      <div className="max-w-6xl mx-auto py-8">
        <div className="animate-pulse space-y-6">
          <div className="h-8 w-48 bg-zinc-200 dark:bg-zinc-800 rounded" />
          <div className="h-64 bg-zinc-200 dark:bg-zinc-800 rounded" />
        </div>
      </div>
    );
  }

  if (error || !catalogo) {
    return (
      <div className="max-w-6xl mx-auto py-8">
        <div className="text-center py-12">
          <p className="text-red-600">Error al cargar catálogo</p>
          <Button variant="outline" className="mt-4" onClick={() => router.push("/dashboard/catalogos")}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Volver
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto py-8">
      <div className="mb-6">
        <Button
          variant="ghost"
          size="sm"
          className="mb-4"
          onClick={() => router.push("/dashboard/catalogos")}
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Catálogos
        </Button>

        <div className="flex flex-wrap items-center gap-4">
          {isEditingName ? (
            <div className="flex items-center gap-2">
              <Input
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="w-64"
                autoFocus
              />
              <Button size="icon" variant="ghost" onClick={handleSaveName}>
                <Check className="w-4 h-4" />
              </Button>
              <Button size="icon" variant="ghost" onClick={handleCancelEditName}>
                <X className="w-4 h-4" />
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
                {catalogo.name}
              </h1>
              <Button size="icon" variant="ghost" onClick={handleStartEditName}>
                <Edit2 className="w-4 h-4" />
              </Button>
              <StatusBadge status={catalogo.status} />
            </div>
          )}

          <div className="flex items-center gap-2 ml-auto">
            <Button
              size="sm"
              onClick={() => setShowAddPicker(true)}
            >
              <Plus className="w-4 h-4 mr-2" />
              Añadir prenda
            </Button>

            {catalogo.status === "draft" ? (
              <Button
                size="sm"
                disabled={catalogo.item_count === 0 || updateMutation.isPending}
                onClick={() => setShowPublishDialog(true)}
              >
                Publicar
              </Button>
            ) : (
              <Button
                size="sm"
                variant="outline"
                disabled={updateMutation.isPending}
                onClick={() => setShowUnpublishDialog(true)}
              >
                Despublicar
              </Button>
            )}

            <Button
              size="sm"
              variant="destructive"
              disabled={deleteMutation.isPending}
              onClick={() => setShowDeleteDialog(true)}
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Eliminar
            </Button>
          </div>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="text-center py-12 border-2 border-dashed rounded-lg">
          <p className="text-lg font-medium text-zinc-700 dark:text-zinc-300">
            Este catálogo está vacío
          </p>
          <p className="text-sm text-muted-foreground mt-2 mb-4">
            Añade prendas desde tus VTONs completados
          </p>
          <Button onClick={() => setShowAddPicker(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Añadir primera prenda
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {items.map((item, idx) => (
            <CatalogItemCard
              key={item.id}
              item={item}
              catalogId={id}
              isFirst={idx === 0}
              isLast={idx === items.length - 1}
              onMoveUp={() => handleMoveUp(item.id)}
              onMoveDown={() => handleMoveDown(item.id)}
            />
          ))}
        </div>
      )}

      <AddItemPicker
        open={showAddPicker}
        onOpenChange={setShowAddPicker}
        catalogId={id}
      />

      <ConfirmDialog
        open={showPublishDialog}
        onOpenChange={setShowPublishDialog}
        title="Publicar catálogo"
        description="¿Estás seguro de que quieres publicar este catálogo? Los compradores podrán ver las prendas."
        confirmLabel="Publicar"
        onConfirm={handlePublish}
        isPending={updateMutation.isPending}
      />

      <ConfirmDialog
        open={showUnpublishDialog}
        onOpenChange={setShowUnpublishDialog}
        title="Despublicar catálogo"
        description="Los compradores ya no podrán ver este catálogo. ¿Continuar?"
        confirmLabel="Despublicar"
        onConfirm={handleUnpublish}
        isPending={updateMutation.isPending}
      />

      <ConfirmDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        title="Eliminar catálogo"
        description="Esta acción no se puede deshacer. Se eliminarán todas las prendas del catálogo."
        confirmLabel="Eliminar"
        cancelLabel="Cancelar"
        onConfirm={handleDelete}
        isPending={deleteMutation.isPending}
        variant="destructive"
      />
    </div>
  );
}
