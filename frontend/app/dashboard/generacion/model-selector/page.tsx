"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { fetchModelosIA, type ModeloIA } from "@/lib/api/modelos-ia";
import { crearGeneracion } from "@/lib/api/generaciones";

const STORAGE_KEY = "ultimo_modelo_id";

export default function ModelSelectorScreen() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const prendaId = searchParams.get("prendaId");

  const [modelos, setModelos] = useState<ModeloIA[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchModelosIA()
      .then(setModelos)
      .catch(() => setError("No se pudieron cargar los modelos"))
      .finally(() => setLoading(false));

    const last = localStorage.getItem(STORAGE_KEY);
    if (last) setSelectedId(last);
  }, []);

  const handleSelect = (id: string, planMinimo: string) => {
    if (planMinimo === "pro") return;
    setSelectedId(id);
    localStorage.setItem(STORAGE_KEY, id);
  };

  const handleGenerate = async () => {
    if (!selectedId || !prendaId) return;
    setSubmitting(true);
    try {
      const generacion = await crearGeneracion(prendaId, selectedId);
      router.push(`/dashboard/generacion/progress?id=${generacion.id}`);
    } catch {
      setError("Error al iniciar la generación");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="p-6 text-center">Cargando modelos...</div>;
  if (error) return <div className="p-6 text-center text-red-500">{error}</div>;

  return (
    <div className="flex min-h-screen flex-col bg-white">
      <header className="border-b p-4">
        <h1 className="text-xl font-semibold">Elige un modelo</h1>
        <p className="text-sm text-gray-500">Selecciona la persona para la prueba virtual</p>
      </header>

      <main className="flex-1 p-4 pb-24">
        <div className="grid grid-cols-2 gap-3">
          {modelos.map((m) => {
            const isPro = m.plan_minimo === "pro";
            const isSelected = selectedId === m.id;
            return (
              <button
                key={m.id}
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
      </main>

      {selectedId && (
        <div className="fixed bottom-0 left-0 right-0 border-t bg-white p-4">
          <button
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
