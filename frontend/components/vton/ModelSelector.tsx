"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Upload, Check, Image as ImageIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

interface ModelItem {
  id: string;
  presigned_url: string;
  name?: string;
}

interface ModelSelectorProps {
  onSelected: (modelId: string) => void;
  selectedId?: string | null;
}

function ModelGrid({
  models,
  selectedId,
  onSelect,
  emptyMessage,
}: {
  models: ModelItem[];
  selectedId?: string | null;
  onSelect: (id: string) => void;
  emptyMessage: string;
}) {
  if (models.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <ImageIcon className="w-8 h-8 text-muted-foreground mb-2" />
        <p className="text-sm text-muted-foreground">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
      {models.map((model) => (
        <button
          key={model.id}
          type="button"
          onClick={() => onSelect(model.id)}
          className={cn(
            "relative aspect-square rounded-lg overflow-hidden border-2 transition-all",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
            selectedId === model.id
              ? "border-primary ring-2 ring-primary/30"
              : "border-border hover:border-primary/50"
          )}
          aria-label={`Seleccionar modelo ${model.name ?? ""}`}
          aria-pressed={selectedId === model.id}
        >
          <img
            src={model.presigned_url}
            alt={model.name ?? "Modelo"}
            className="w-full h-full object-cover"
          />
          {selectedId === model.id && (
            <div className="absolute top-1 right-1 bg-primary text-white rounded-full p-0.5">
              <Check className="w-3 h-3" />
            </div>
          )}
        </button>
      ))}
    </div>
  );
}

function ModelUploader({ onUploaded }: { onUploaded: () => void }) {
  const [isUploading, setIsUploading] = useState(false);

  const handleFile = useCallback(
    async (file: File) => {
      if (!file.type.startsWith("image/")) {
        toast.error("Solo se permiten imágenes");
        return;
      }

      setIsUploading(true);
      try {
        const formData = new FormData();
        formData.append("file", file);

        await apiFetch("/api/media/models", {
          method: "POST",
          body: formData,
        });

        toast.success("Modelo subido correctamente");
        onUploaded();
      } catch (err) {
        const message = err instanceof Error ? err.message : "Error al subir el modelo";
        toast.error(message);
      } finally {
        setIsUploading(false);
      }
    },
    [onUploaded]
  );

  return (
    <div className="flex flex-col items-center gap-3 py-4">
      <p className="text-sm text-muted-foreground">
        No tienes modelos propios aún
      </p>
      <Button
        variant="outline"
        size="sm"
        disabled={isUploading}
        onClick={() => document.getElementById("model-file-input")?.click()}
      >
        <Upload className="w-4 h-4 mr-1" />
        {isUploading ? "Subiendo..." : "Subir tu propio modelo"}
      </Button>
      <input
        id="model-file-input"
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
        }}
      />
    </div>
  );
}

export function ModelSelector({ onSelected, selectedId }: ModelSelectorProps) {
  const [myModels, setMyModels] = useState<ModelItem[]>([]);
  const [curatedModels, setCuratedModels] = useState<ModelItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("my-models");

  const fetchMyModels = useCallback(async () => {
    try {
      const data = await apiFetch("/api/media/models/mine");
      setMyModels(Array.isArray(data) ? data : []);
    } catch {
      toast.error("Error al cargar tus modelos");
      setMyModels([]);
    }
  }, []);

  const fetchCuratedModels = useCallback(async () => {
    try {
      const data = await apiFetch("/api/media/models/curated");
      setCuratedModels(Array.isArray(data) ? data : []);
    } catch {
      toast.error("Error al cargar la biblioteca de modelos");
      setCuratedModels([]);
    }
  }, []);

  useEffect(() => {
    async function load() {
      setLoading(true);
      await Promise.all([fetchMyModels(), fetchCuratedModels()]);
      setLoading(false);
    }
    load();
  }, [fetchMyModels, fetchCuratedModels]);

  const handleSelect = useCallback(
    (id: string) => {
      onSelected(id);
    },
    [onSelected]
  );

  if (loading) {
    return (
      <div className="space-y-3">
        <div className="flex gap-2">
          <Skeleton className="h-9 w-24" />
          <Skeleton className="h-9 w-24" />
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="aspect-square rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <Tabs value={activeTab} onValueChange={setActiveTab}>
      <TabsList className="w-full sm:w-auto">
        <TabsTrigger value="my-models" className="flex-1 sm:flex-none">
          Mis Modelos
        </TabsTrigger>
        <TabsTrigger value="library" className="flex-1 sm:flex-none">
          Biblioteca
        </TabsTrigger>
      </TabsList>

      <TabsContent value="my-models" className="mt-4">
        {myModels.length === 0 ? (
          <ModelUploader onUploaded={fetchMyModels} />
        ) : (
          <ModelGrid
            models={myModels}
            selectedId={selectedId}
            onSelect={handleSelect}
            emptyMessage="No tienes modelos propios"
          />
        )}
      </TabsContent>

      <TabsContent value="library" className="mt-4">
        <ModelGrid
          models={curatedModels}
          selectedId={selectedId}
          onSelect={handleSelect}
          emptyMessage="La biblioteca está vacía"
        />
      </TabsContent>
    </Tabs>
  );
}
