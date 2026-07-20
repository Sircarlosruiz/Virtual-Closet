"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Check, ImagePlus, Plus, Sparkles, Upload, X } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
  createModel,
  listModelPoses,
  listModels,
  uploadModelPose,
  type ModelPose,
  type ModelSummary,
  type PoseType,
} from "@/lib/api/model-poses";

const POSES: { value: PoseType; label: string; note: string }[] = [
  { value: "front", label: "Frente", note: "Vista principal" },
  { value: "side", label: "Perfil", note: "Vista lateral" },
  { value: "back", label: "Espalda", note: "Vista posterior" },
];

export function ModelPoseManagement() {
  const [models, setModels] = useState<ModelSummary[]>([]);
  const [selected, setSelected] = useState<ModelSummary | null>(null);
  const [poses, setPoses] = useState<ModelPose[]>([]);
  const [name, setName] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  const refreshModels = useCallback(async () => {
    try {
      const nextModels = await listModels();
      setModels(nextModels);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "No se pudieron cargar los modelos");
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    listModels()
      .then((nextModels) => {
        if (!cancelled) setModels(nextModels);
      })
      .catch((error) => {
        if (!cancelled) toast.error(error instanceof Error ? error.message : "No se pudieron cargar los modelos");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selected) return;
    listModelPoses(selected.id)
      .then(setPoses)
      .catch(() => toast.error("No se pudieron cargar las poses"));
  }, [selected]);

  const usedPoses = useMemo(() => new Set(poses.map((pose) => pose.pose)), [poses]);

  async function handleCreate() {
    const trimmedName = name.trim();
    if (!trimmedName) return;
    setIsCreating(true);
    try {
      const model = await createModel(trimmedName);
      setName("");
      setSelected(model);
      setModels((current) => [model, ...current]);
      toast.success("Modelo creado");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "No se pudo crear el modelo");
    } finally {
      setIsCreating(false);
    }
  }

  async function handleUpload(file: File, pose: PoseType) {
    if (!selected) return;
    setIsUploading(true);
    try {
      await uploadModelPose(selected.id, file, pose);
      setPoses(await listModelPoses(selected.id));
      await refreshModels();
      toast.success(`Pose ${POSES.find((item) => item.value === pose)?.label} guardada`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "No se pudo subir la pose");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div className="mx-auto grid max-w-6xl gap-8 px-4 py-8 lg:grid-cols-[0.8fr_1.2fr]">
      <section className="space-y-5">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary">Archivo de poses</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight">Tus modelos</h1>
            <p className="mt-2 max-w-md text-sm text-muted-foreground">Construye una identidad visual con hasta tres ángulos. Una buena base hace que cada generación se sienta más real.</p>
          </div>
          <Sparkles className="hidden h-8 w-8 text-primary/70 sm:block" />
        </div>

        <Card className="border-primary/20 bg-primary/[0.04]">
          <CardContent className="flex gap-3 p-4">
            <Plus className="mt-0.5 h-5 w-5 text-primary" />
            <div className="flex-1 space-y-3">
              <p className="text-sm font-medium">Nuevo modelo</p>
              <div className="flex gap-2">
                <Input value={name} onChange={(event) => setName(event.target.value)} placeholder="Nombre, por ejemplo María" onKeyDown={(event) => event.key === "Enter" && void handleCreate()} />
                <Button onClick={() => void handleCreate()} disabled={!name.trim() || isCreating}>{isCreating ? "Creando" : "Crear"}</Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="space-y-2">
          {models.map((model) => (
            <button key={model.id} type="button" onClick={() => setSelected(model)} className={cn("flex w-full items-center justify-between rounded-xl border bg-card p-4 text-left transition hover:border-primary/50", selected?.id === model.id && "border-primary bg-primary/[0.04] shadow-sm")}>
              <span><span className="block font-medium">{model.name}</span><span className="mt-1 block text-xs text-muted-foreground">{model.pose_count}/3 poses registradas</span></span>
              <span className={cn("rounded-full px-2.5 py-1 text-xs font-medium", model.pose_count === 3 ? "bg-emerald-100 text-emerald-700" : "bg-muted text-muted-foreground")}>{model.pose_count === 3 ? "Completo" : "En construcción"}</span>
            </button>
          ))}
          {models.length === 0 && <div className="rounded-xl border border-dashed p-8 text-center text-sm text-muted-foreground">Crea tu primer modelo para comenzar.</div>}
        </div>
      </section>

      <section>
        {!selected ? (
          <Card className="flex min-h-[440px] items-center justify-center border-dashed"><CardContent className="text-center"><ImagePlus className="mx-auto h-10 w-10 text-muted-foreground/50" /><p className="mt-4 font-medium">Selecciona un modelo</p><p className="mt-1 text-sm text-muted-foreground">Aquí aparecerán sus tres vistas.</p></CardContent></Card>
        ) : (
          <Card className="overflow-hidden">
            <CardHeader className="border-b bg-muted/20"><div className="flex items-start justify-between"><div><p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">Modelo seleccionado</p><CardTitle className="mt-1">{selected.name}</CardTitle></div><Button variant="ghost" size="icon" onClick={() => setSelected(null)} aria-label="Cerrar modelo"><X className="h-4 w-4" /></Button></div></CardHeader>
            <CardContent className="grid gap-4 p-5 sm:grid-cols-3">
              {POSES.map(({ value, label, note }) => {
                const photo = poses.find((item) => item.pose === value);
                 return <div key={value} className="overflow-hidden rounded-xl border bg-background"><div className="aspect-[4/5] bg-muted">{photo ? <img src={photo.presigned_url} alt={`${selected.name}, ${label}`} className="h-full w-full object-cover" /> : <div className="flex h-full flex-col items-center justify-center p-4 text-center"><ImagePlus className="h-7 w-7 text-muted-foreground/50" /><p className="mt-2 text-sm font-medium">{label}</p><p className="text-xs text-muted-foreground">{note}</p></div>}</div><div className="flex items-center justify-between p-3"><div><p className="text-sm font-medium">{label}</p><p className="text-xs text-muted-foreground">{photo ? "Lista" : "Sin foto"}</p></div>{photo ? <Check className="h-4 w-4 text-emerald-600" /> : <label className={cn("inline-flex cursor-pointer items-center rounded-md border px-3 py-2 text-sm font-medium", isUploading && "pointer-events-none opacity-50")}><span className="sr-only">Subir pose {label}</span><Upload className="mr-1 h-3.5 w-3.5" />Subir<input type="file" accept="image/jpeg,image/png" className="hidden" disabled={isUploading} onChange={(event) => { const file = event.target.files?.[0]; if (file) void handleUpload(file, value); event.currentTarget.value = ""; }} /></label>}</div>{usedPoses.has(value) && <span className="sr-only">Pose ya utilizada</span>}</div>;
              })}
            </CardContent>
          </Card>
        )}
      </section>
    </div>
  );
}
