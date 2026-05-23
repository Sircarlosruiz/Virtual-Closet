"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  fetchModelosIA,
  getModeloUploadUrl,
  crearModelo,
  type ModeloIA,
} from "@/lib/api/modelos-ia";
import { crearGeneracion } from "@/lib/api/generaciones";
import { isValidUuid } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ImageDropzone } from "@/components/prendas/ImageDropzone";
import { toast } from "sonner";

const STORAGE_KEY = "ultimo_modelo_id";

function ModelSelectorScreen() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const prendaId = searchParams.get("prendaId");

  const [modelos, setModelos] = useState<ModeloIA[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createNombre, setCreateNombre] = useState("");
  const [createDescripcion, setCreateDescripcion] = useState("");
  const [createFile, setCreateFile] = useState<File | null>(null);
  const [createFileError, setCreateFileError] = useState<string>();
  const [createFormKey, setCreateFormKey] = useState(0);
  const [createProgress, setCreateProgress] = useState(0);
  const [createStatus, setCreateStatus] = useState<"idle" | "uploading" | "done" | "error">("idle");

  const canSubmitCreate =
    !!createFile && !!createNombre.trim() && createStatus !== "uploading";

  const missingCreateFields = [
    !createFile && "imagen del modelo",
    !createNombre.trim() && "nombre",
  ].filter(Boolean) as string[];

  useEffect(() => {
    fetchModelosIA()
      .then((loaded) => {
        setModelos(loaded);
        const last = localStorage.getItem(STORAGE_KEY);
        const restored = loaded.find((m) => m.id === last && m.plan_minimo !== "pro");
        if (restored) {
          setSelectedId(restored.id);
        } else if (last) {
          localStorage.removeItem(STORAGE_KEY);
        }
      })
      .catch(() => setLoadError("No se pudieron cargar los modelos"))
      .finally(() => setLoading(false));
  }, []);

  const handleSelect = (id: string, planMinimo: string) => {
    if (planMinimo === "pro") return;
    setSelectedId(id);
    localStorage.setItem(STORAGE_KEY, id);
  };

  const canGenerate =
    isValidUuid(prendaId) &&
    isValidUuid(selectedId) &&
    modelos.some((m) => m.id === selectedId && m.plan_minimo !== "pro");

  const handleGenerate = async () => {
    if (!canGenerate) {
      setSubmitError(
        !isValidUuid(prendaId)
          ? "Falta la prenda. Vuelve al catálogo y abre una prenda en estado Lista."
          : "Selecciona un modelo válido antes de generar."
      );
      return;
    }
    setSubmitting(true);
    setSubmitError(null);
    try {
      const generacion = await crearGeneracion(prendaId!, selectedId!);
      router.push(`/dashboard/generacion/progress?id=${generacion.id}`);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Error al iniciar la generación");
    } finally {
      setSubmitting(false);
    }
  };

  const handleCreateModelo = async () => {
    if (!createFile) {
      toast.error("Selecciona una imagen");
      return;
    }
    if (!createNombre.trim()) {
      toast.error("Ingresa un nombre para el modelo");
      return;
    }

    setCreateStatus("uploading");
    setCreateProgress(0);

    try {
      const extension = createFile.name.split(".").pop()?.toLowerCase() || "jpg";
      const { upload_url, modelo_id, object_key } = await getModeloUploadUrl(extension);

      const xhr = new XMLHttpRequest();
      xhr.open("PUT", upload_url, true);
      xhr.setRequestHeader("Content-Type", createFile.type || "image/jpeg");

      xhr.upload.addEventListener("progress", (e) => {
        if (e.lengthComputable) {
          setCreateProgress((e.loaded / e.total) * 100);
        }
      });

      xhr.addEventListener("load", async () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          setCreateProgress(100);
          setCreateStatus("done");

          try {
            const modelo = await crearModelo({
              modelo_id,
              nombre: createNombre.trim(),
              descripcion: createDescripcion.trim() || undefined,
              object_key,
            });
            toast.success("Modelo creado correctamente");
            setModelos((prev) => [...prev, modelo]);
            setSelectedId(modelo.id);
            setShowCreateForm(false);
            setCreateFile(null);
            setCreateFileError(undefined);
            setCreateNombre("");
            setCreateDescripcion("");
            setCreateStatus("idle");
            setCreateFormKey((k) => k + 1);
          } catch (err: any) {
            toast.error(err.message || "Error al registrar el modelo");
            setCreateStatus("error");
          }
        } else {
          toast.error("Error al subir la imagen");
          setCreateStatus("error");
        }
      });

      xhr.addEventListener("error", () => {
        toast.error("Error de red al subir");
        setCreateStatus("error");
      });

      xhr.send(createFile);
    } catch (err: any) {
      toast.error(err.message || "Error inesperado");
      setCreateStatus("error");
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen flex-col bg-white">
        <header className="border-b p-4">
          <h1 className="text-xl font-semibold">Elige un modelo</h1>
          <p className="text-sm text-gray-500">Selecciona la persona para la prueba virtual</p>
        </header>
        <div className="flex flex-1 items-center justify-center p-6 text-gray-500">
          Cargando modelos...
        </div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="flex min-h-screen flex-col bg-white">
        <header className="border-b p-4">
          <h1 className="text-xl font-semibold">Elige un modelo</h1>
          <p className="text-sm text-gray-500">Selecciona la persona para la prueba virtual</p>
        </header>
        <div className="flex flex-1 flex-col items-center justify-center gap-4 p-6">
          <p className="text-center text-red-500">{loadError}</p>
          <button
            type="button"
            onClick={() => setShowCreateForm(true)}
            className="rounded-lg bg-blue-600 px-6 py-2.5 font-semibold text-white hover:bg-blue-700"
          >
            Crear modelo personalizado
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-white">
      <header className="border-b p-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">Elige un modelo</h1>
            <p className="text-sm text-gray-500">Selecciona la persona para la prueba virtual</p>
          </div>
          <button
            type="button"
            onClick={() => setShowCreateForm(true)}
            className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            + Nuevo modelo
          </button>
        </div>
      </header>

      <main className="flex-1 p-4 pb-24">
        {!isValidUuid(prendaId) && (
          <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            <p>
              No se detectó una prenda válida en la URL. Abre el catálogo y haz clic en una prenda con
              estado &quot;Lista&quot; (o sube una nueva).
            </p>
            <Link
              href="/dashboard"
              className="mt-2 inline-block font-medium text-amber-950 underline underline-offset-2"
            >
              Ir al catálogo
            </Link>
          </div>
        )}
        {submitError && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {submitError}
          </div>
        )}

        {showCreateForm ? (
          <div className="max-w-md mx-auto space-y-4 rounded-xl border p-4 bg-gray-50">
            <h2 className="text-lg font-semibold">Crear modelo personalizado</h2>

            <div>
              <label className="text-sm font-medium">
                Imagen del modelo <span className="text-red-600">*</span>
              </label>
              <div className="mt-1">
                <ImageDropzone
                  key={createFormKey}
                  onFileSelected={(file) => {
                    setCreateFile(file);
                    setCreateFileError(undefined);
                  }}
                  error={createFileError}
                />
              </div>
            </div>

            <div>
              <label className="text-sm font-medium">Nombre</label>
              <Input
                value={createNombre}
                onChange={(e) => setCreateNombre(e.target.value.slice(0, 100))}
                placeholder="Ej: Modelo Ana"
                maxLength={100}
              />
            </div>

            <div>
              <label className="text-sm font-medium">Descripción (opcional)</label>
              <Input
                value={createDescripcion}
                onChange={(e) => setCreateDescripcion(e.target.value.slice(0, 500))}
                placeholder="Ej: Mujer, 25 años, talla M"
                maxLength={500}
              />
            </div>

            {createStatus === "uploading" && (
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all"
                  style={{ width: `${createProgress}%` }}
                />
              </div>
            )}

            {createStatus === "error" && (
              <p className="text-sm text-red-600">Error al crear el modelo. Intenta de nuevo.</p>
            )}

            {missingCreateFields.length > 0 && createStatus !== "uploading" && (
              <p className="text-sm text-amber-800">
                Para continuar, completa: {missingCreateFields.join(" y ")}.
              </p>
            )}

            <div className="flex gap-3">
              <Button
                variant="outline"
                onClick={() => {
                  setShowCreateForm(false);
                  setCreateStatus("idle");
                  setCreateFile(null);
                  setCreateFileError(undefined);
                  setCreateNombre("");
                  setCreateDescripcion("");
                  setCreateFormKey((k) => k + 1);
                }}
                className="flex-1"
              >
                Cancelar
              </Button>
              <Button
                onClick={() => {
                  if (!createFile) {
                    setCreateFileError("Selecciona una imagen del modelo");
                    return;
                  }
                  if (!createNombre.trim()) {
                    toast.error("Ingresa un nombre para el modelo");
                    return;
                  }
                  handleCreateModelo();
                }}
                disabled={!canSubmitCreate}
                className="flex-1"
              >
                {createStatus === "uploading" ? "Subiendo..." : "Crear modelo"}
              </Button>
            </div>
          </div>
        ) : modelos.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-4 py-16 text-center">
            <p className="font-medium text-gray-700">No hay modelos disponibles</p>
            <p className="text-sm text-gray-500">
              Crea tu primer modelo personalizado subiendo una foto.
            </p>
            <button
              type="button"
              onClick={() => setShowCreateForm(true)}
              className="rounded-lg bg-blue-600 px-6 py-2.5 font-semibold text-white hover:bg-blue-700"
            >
              Crear modelo personalizado
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {modelos.map((m) => {
              const isPro = m.plan_minimo === "pro";
              const isSelected = selectedId === m.id;
              return (
                <button
                  key={m.id}
                  type="button"
                  disabled={isPro}
                  onClick={() => handleSelect(m.id, m.plan_minimo)}
                  className={`relative flex items-center gap-3 rounded-xl border-2 p-3 transition-all ${
                    isSelected
                      ? "border-blue-500 bg-blue-50"
                      : isPro
                        ? "border-gray-200 bg-gray-50 opacity-60"
                        : "border-gray-200 bg-white active:scale-95"
                  }`}
                >
                  <img
                    src={m.thumbnail_url}
                    alt={m.nombre}
                    className="h-14 w-14 rounded-full object-cover"
                  />
                  <div className="flex-1 text-left">
                    <p className="font-medium text-sm">{m.nombre}</p>
                    <p className="text-xs text-gray-500 line-clamp-2">{m.descripcion}</p>
                  </div>
                  {isPro && (
                    <span className="absolute right-2 top-2 text-gray-400">
                      <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                      </svg>
                    </span>
                  )}
                  {isSelected && !isPro && (
                    <span className="absolute right-2 top-2 text-blue-500">
                      <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </main>

      {canGenerate && (
        <div className="fixed bottom-0 left-0 right-0 border-t bg-white p-4">
          <button
            type="button"
            onClick={handleGenerate}
            disabled={submitting}
            className="w-full rounded-xl bg-blue-600 py-3 font-semibold text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? "Iniciando..." : "Generar"}
          </button>
        </div>
      )}
    </div>
  );
}

export default function ModelSelectorPage() {
  return (
    <Suspense fallback={<div className="p-6 text-center">Cargando...</div>}>
      <ModelSelectorScreen />
    </Suspense>
  );
}
