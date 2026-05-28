"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useAddCatalogoItem, useCatalogosList } from "@/hooks/useCatalogos";
import { fetchGeneracion, type GeneracionResponse } from "@/lib/api/generaciones";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { CreateCatalogModal } from "@/components/catalogos/CreateCatalogModal";

const formSchema = z.object({
  catalog_id: z.string().min(1, "Selecciona un catálogo"),
  garment_name: z.string().min(1, "El nombre es obligatorio").max(200),
  price: z.number().min(0, "El precio debe ser mayor o igual a 0"),
  cloth_type: z.enum(["upper_body", "lower_body", "dress"]),
  sku: z.string().min(1, "El SKU es obligatorio").max(100),
});

type FormValues = z.infer<typeof formSchema>;

const CLOTH_TYPE_LABELS: Record<FormValues["cloth_type"], string> = {
  upper_body: "Parte superior",
  lower_body: "Parte inferior",
  dress: "Vestido",
};

interface AddGeneracionToCatalogFormProps {
  generacionId: string;
}

export function AddGeneracionToCatalogForm({
  generacionId,
}: AddGeneracionToCatalogFormProps) {
  const router = useRouter();
  const [generacion, setGeneracion] = useState<GeneracionResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const { data: catalogsData, isLoading: catalogsLoading } = useCatalogosList(1, 50);
  const addMutation = useAddCatalogoItem();

  const catalogs = catalogsData?.catalogs ?? [];

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      catalog_id: "",
      garment_name: "",
      price: 0,
      cloth_type: "upper_body",
      sku: "",
    },
    mode: "onChange",
  });

  const selectedCatalogId = watch("catalog_id");

  useEffect(() => {
    fetchGeneracion(generacionId)
      .then((gen) => {
        if (gen.estado !== "lista") {
          setLoadError("La generación aún no está lista para agregarse al catálogo");
          return;
        }
        setGeneracion(gen);
        setValue("garment_name", `Prenda ${gen.id.slice(0, 8)}`);
        setValue("sku", `SKU-${gen.id.slice(0, 8).toUpperCase()}`);
      })
      .catch(() => setLoadError("No se pudo cargar la generación"));
  }, [generacionId, setValue]);

  useEffect(() => {
    if (!selectedCatalogId && catalogs.length > 0) {
      setValue("catalog_id", catalogs[0].id);
    }
  }, [catalogs, selectedCatalogId, setValue]);

  const onSubmit = (values: FormValues) => {
    addMutation.mutate(
      {
        catalogId: values.catalog_id,
        input: {
          generacion_id: generacionId,
          garment_name: values.garment_name,
          price: Number(values.price),
          cloth_type: values.cloth_type,
          sku: values.sku,
        },
      },
      {
        onSuccess: () => {
          router.push(`/dashboard/catalogos/${values.catalog_id}`);
        },
      }
    );
  };

  if (loadError) {
    return (
      <div className="mx-auto max-w-lg p-6 text-center">
        <p className="text-red-600">{loadError}</p>
        <Button
          variant="outline"
          className="mt-4"
          onClick={() => router.push(`/dashboard/generacion/result?id=${generacionId}`)}
        >
          Volver al resultado
        </Button>
      </div>
    );
  }

  if (!generacion) {
    return <div className="p-6 text-center text-muted-foreground">Cargando...</div>;
  }

  return (
    <div className="mx-auto max-w-lg space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
          Agregar al catálogo
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Elige el catálogo y completa los datos de la prenda.
        </p>
      </div>

      {generacion.imagen_url && (
        <div className="aspect-[3/4] overflow-hidden rounded-lg border bg-zinc-100">
          <img
            src={generacion.imagen_url}
            alt="Vista previa de la generación"
            className="h-full w-full object-contain"
          />
        </div>
      )}

      {catalogsLoading ? (
        <p className="text-sm text-muted-foreground">Cargando catálogos...</p>
      ) : catalogs.length === 0 ? (
        <div className="rounded-lg border border-dashed p-4 text-center">
          <p className="mb-3 text-sm text-muted-foreground">
            Aún no tienes catálogos. Crea uno para agregar esta prenda.
          </p>
          <Button type="button" onClick={() => setShowCreateModal(true)}>
            Crear catálogo
          </Button>
        </div>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="catalog_id">Catálogo</Label>
            <select
              id="catalog_id"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              {...register("catalog_id")}
            >
              <option value="">Selecciona un catálogo</option>
              {catalogs.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.item_count} prendas)
                </option>
              ))}
            </select>
            {errors.catalog_id && (
              <p className="text-sm text-red-500">{errors.catalog_id.message}</p>
            )}
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="px-0"
              onClick={() => setShowCreateModal(true)}
            >
              + Crear otro catálogo
            </Button>
          </div>

          <div className="space-y-2">
            <Label htmlFor="garment_name">Nombre</Label>
            <Input id="garment_name" placeholder="Camisa blanca" {...register("garment_name")} />
            {errors.garment_name && (
              <p className="text-sm text-red-500">{errors.garment_name.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="price">Precio</Label>
            <Input
              id="price"
              type="number"
              step="0.01"
              min="0"
              {...register("price", { valueAsNumber: true })}
            />
            {errors.price && (
              <p className="text-sm text-red-500">{errors.price.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="cloth_type">Tipo de prenda</Label>
            <select
              id="cloth_type"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              {...register("cloth_type")}
            >
              {(Object.keys(CLOTH_TYPE_LABELS) as FormValues["cloth_type"][]).map(
                (value) => (
                  <option key={value} value={value}>
                    {CLOTH_TYPE_LABELS[value]}
                  </option>
                )
              )}
            </select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="sku">SKU</Label>
            <Input id="sku" placeholder="SKU-001" {...register("sku")} />
            {errors.sku && (
              <p className="text-sm text-red-500">{errors.sku.message}</p>
            )}
          </div>

          <div className="flex gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              className="flex-1"
              onClick={() =>
                router.push(`/dashboard/generacion/result?id=${generacionId}`)
              }
            >
              Cancelar
            </Button>
            <Button type="submit" className="flex-1" disabled={addMutation.isPending}>
              {addMutation.isPending ? "Agregando..." : "Agregar al catálogo"}
            </Button>
          </div>
        </form>
      )}

      <CreateCatalogModal
        open={showCreateModal}
        onOpenChange={setShowCreateModal}
      />
    </div>
  );
}
