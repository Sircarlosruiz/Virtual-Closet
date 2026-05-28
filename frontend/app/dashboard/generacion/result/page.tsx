"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { fetchGeneracion, fetchGeneracionesByPrenda, type GeneracionResponse } from "@/lib/api/generaciones";

function GenerationResultScreen() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const generacionId = searchParams.get("id");

  const [generacion, setGeneracion] = useState<GeneracionResponse | null>(null);
  const [historial, setHistorial] = useState<GeneracionResponse[]>([]);
  const [showOriginal, setShowOriginal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!generacionId) return;

    fetchGeneracion(generacionId)
      .then((gen) => {
        setGeneracion(gen);
        return fetchGeneracionesByPrenda(gen.prenda_id);
      })
      .then((hist) => {
        setHistorial(hist.filter((h) => h.id !== generacionId));
      })
      .catch(() => setError("No se pudo cargar el resultado"))
      .finally(() => setLoading(false));
  }, [generacionId]);

  if (loading) return <div className="p-6 text-center">Cargando resultado...</div>;
  if (error) return <div className="p-6 text-center text-red-500">{error}</div>;
  if (!generacion) {
    return <div className="p-6 text-center">Resultado no encontrado</div>;
  }

  if (generacion.estado === "error") {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-white p-6">
        <div className="mb-4 text-4xl">❌</div>
        <h2 className="mb-2 text-xl font-semibold">Error en la generación</h2>
        <p className="mb-6 text-center text-gray-500">{generacion.error_message}</p>
        <button
          onClick={() => router.push(`/dashboard/generacion/model-selector?prendaId=${generacion.prenda_id}`)}
          className="rounded-xl bg-blue-600 px-6 py-3 font-semibold text-white hover:bg-blue-700"
        >
          Reintentar
        </button>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-black">
      <div className="relative flex-1">
        {generacion.imagen_url && (
          <img
            src={generacion.imagen_url}
            alt="Generación IA"
            className={`h-[calc(100vh-140px)] w-full object-contain transition-opacity duration-300 ${
              showOriginal ? "opacity-0" : "opacity-100"
            }`}
          />
        )}
        {showOriginal && generacion.thumbnail_url && (
          <img
            src={generacion.thumbnail_url}
            alt="Original"
            className="absolute inset-0 h-[calc(100vh-140px)] w-full object-contain transition-opacity duration-300"
          />
        )}
      </div>

      <div className="border-t bg-white p-4">
        <div className="mb-3 flex gap-2">
          <button
            onClick={() => setShowOriginal(!showOriginal)}
            className="flex-1 rounded-lg border border-gray-300 py-2 text-sm font-medium transition-colors hover:bg-gray-50"
          >
            {showOriginal ? "Ver generado" : "Ver original"}
          </button>
          <button
            onClick={() =>
              router.push(
                `/dashboard/catalogos/agregar?generacionId=${generacion.id}`
              )
            }
            disabled={generacion.estado !== "lista"}
            className="flex-1 rounded-lg bg-blue-600 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Agregar al catálogo
          </button>
        </div>
        <button
          onClick={() => router.push(`/dashboard/generacion/model-selector?prendaId=${generacion.prenda_id}`)}
          className="w-full rounded-lg bg-gray-900 py-2.5 text-sm font-medium text-white transition-colors hover:bg-gray-800"
        >
          Regenerar con otro modelo
        </button>
      </div>

      {historial.length > 0 && (
        <div className="border-t bg-white p-4">
          <p className="mb-2 text-sm font-medium text-gray-600">Generaciones anteriores</p>
          <div className="flex gap-2 overflow-x-auto">
            {historial.map((h) => (
              <button
                key={h.id}
                onClick={() => router.push(`/dashboard/generacion/result?id=${h.id}`)}
                className="h-16 w-16 flex-shrink-0 overflow-hidden rounded-lg border"
              >
                {h.thumbnail_url && (
                  <img src={h.thumbnail_url} alt="" className="h-full w-full object-cover" />
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function GenerationResultPage() {
  return (
    <Suspense fallback={<div className="p-6 text-center">Cargando resultado...</div>}>
      <GenerationResultScreen />
    </Suspense>
  );
}
