"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useAddCatalogoItem } from "@/hooks/useCatalogos";
import { getVTONJobs, VTONJobHistoryItem } from "@/lib/api/vton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

const formSchema = z.object({
  garment_name: z.string().min(1, "El nombre es obligatorio").max(200),
  price: z.number().min(0, "El precio debe ser mayor o igual a 0"),
  sku: z.string().min(1, "El SKU es obligatorio").max(100),
});

type FormValues = z.infer<typeof formSchema>;

interface AddItemPickerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  catalogId: string;
}

export function AddItemPicker({ open, onOpenChange, catalogId }: AddItemPickerProps) {
  const [jobs, setJobs] = useState<VTONJobHistoryItem[]>([]);
  const [selectedJob, setSelectedJob] = useState<VTONJobHistoryItem | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const addMutation = useAddCatalogoItem();

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { garment_name: "", price: 0, sku: "" },
    mode: "onChange",
  });

  useEffect(() => {
    if (open) {
      setIsLoading(true);
      getVTONJobs(1, 50)
        .then((res) => {
          const completed = res.items.filter((j) => j.status === "completed");
          setJobs(completed);
        })
        .catch(() => setJobs([]))
        .finally(() => setIsLoading(false));
    }
  }, [open]);

  const onSubmit = (values: FormValues) => {
    if (!selectedJob) return;
    addMutation.mutate(
      {
        catalogId,
        input: {
          vton_job_id: selectedJob.job_id,
          garment_name: values.garment_name,
          price: Number(values.price),
          cloth_type: selectedJob.cloth_type,
          sku: values.sku,
        },
      },
      {
        onSuccess: () => {
          onOpenChange(false);
          reset();
          setSelectedJob(null);
        },
      }
    );
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <AlertDialogHeader>
          <AlertDialogTitle>Añadir prenda al catálogo</AlertDialogTitle>
          <AlertDialogDescription>
            Selecciona un VTON completado y completa los datos de la prenda.
          </AlertDialogDescription>
        </AlertDialogHeader>

        {!selectedJob ? (
          <div className="space-y-4">
            {isLoading ? (
              <p className="text-sm text-muted-foreground">Cargando...</p>
            ) : jobs.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No hay VTONs completados disponibles.
              </p>
            ) : (
              <div className="grid grid-cols-3 gap-3">
                {jobs.map((job) => (
                  <button
                    key={job.job_id}
                    type="button"
                    className="relative aspect-square bg-zinc-100 dark:bg-zinc-800 rounded-lg overflow-hidden border-2 border-transparent hover:border-primary transition-colors"
                    onClick={() => {
                      setSelectedJob(job);
                      setValue("garment_name", `Prenda ${job.job_id.slice(0, 8)}`);
                    }}
                  >
                    {job.result_url && (
                      <img
                        src={job.result_url}
                        alt="VTON result"
                        className="w-full h-full object-cover"
                      />
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex gap-4">
              <div className="w-32 h-32 bg-zinc-100 dark:bg-zinc-800 rounded-lg overflow-hidden flex-shrink-0">
                {selectedJob.result_url && (
                  <img
                    src={selectedJob.result_url}
                    alt="Selected"
                    className="w-full h-full object-cover"
                  />
                )}
              </div>
              <div className="flex-1">
                <p className="text-sm text-muted-foreground">
                  Tipo: {selectedJob.cloth_type.replace("_", " ")}
                </p>
                <Button
                  variant="ghost"
                  size="sm"
                  className="mt-2"
                  onClick={() => setSelectedJob(null)}
                >
                  Cambiar selección
                </Button>
              </div>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="garment_name">Nombre</Label>
                <Input id="garment_name" placeholder="Camisa blanca" {...register("garment_name")} />
                {errors.garment_name && (
                  <p className="text-sm text-red-500">{errors.garment_name.message}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="price">Precio</Label>
                <Input id="price" type="number" step="0.01" min="0" {...register("price", { valueAsNumber: true })} />
                {errors.price && (
                  <p className="text-sm text-red-500">{errors.price.message}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="sku">SKU</Label>
                <Input id="sku" placeholder="SKU-001" {...register("sku")} />
                {errors.sku && (
                  <p className="text-sm text-red-500">{errors.sku.message}</p>
                )}
              </div>
              <AlertDialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    onOpenChange(false);
                    setSelectedJob(null);
                  }}
                >
                  Cancelar
                </Button>
                <Button type="submit" disabled={addMutation.isPending}>
                  {addMutation.isPending ? "Añadiendo..." : "Añadir"}
                </Button>
              </AlertDialogFooter>
            </form>
          </div>
        )}
      </AlertDialogContent>
    </AlertDialog>
  );
}
