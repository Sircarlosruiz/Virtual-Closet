"use client";

import { Suspense, useEffect, useState, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { fetchMe } from "@/lib/api/auth";
import { fetchGeneracion } from "@/lib/api/generaciones";

const STEPS = [
  { label: "Analizando prenda...", icon: "🔍" },
  { label: "Aplicando modelo...", icon: "✨" },
  { label: "Finalizando...", icon: "🎨" },
];

const POLL_INTERVAL_MS = 3000;
const TIMEOUT_MS = 300_000;

function ProgressScreen() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const generacionId = searchParams.get("id");

  const [currentStep, setCurrentStep] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const finishedRef = useRef(false);

  useEffect(() => {
    if (!generacionId) return;

    const timer = setInterval(() => setElapsed((s) => s + 1), 1000);

    const stepTimer = setInterval(() => {
      setCurrentStep((s) => Math.min(s + 1, STEPS.length - 1));
    }, 30000);

    let ws: WebSocket | null = null;

    const finishWithResult = () => {
      if (finishedRef.current) return;
      finishedRef.current = true;
      router.push(`/dashboard/generacion/result?id=${generacionId}`);
    };

    const finishWithError = (message: string) => {
      if (finishedRef.current) return;
      finishedRef.current = true;
      setError(message || "Error en la generación");
    };

    const pollStatus = async () => {
      if (finishedRef.current) return;
      try {
        const generacion = await fetchGeneracion(generacionId);
        if (generacion.estado === "lista") {
          finishWithResult();
        } else if (generacion.estado === "error") {
          finishWithError(generacion.error_message || "Error en la generación");
        }
      } catch {
        // ignore transient poll errors
      }
    };

    const pollInterval = setInterval(pollStatus, POLL_INTERVAL_MS);
    pollStatus();

    const timeoutId = setTimeout(() => {
      finishWithError("La generación está tardando demasiado. Por favor, reintenta.");
    }, TIMEOUT_MS);

    fetchMe()
      .then((me) => {
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
        const wsUrl = backendUrl.replace("http", "ws") + `/api/ws/${me.id}`;
        ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === "generacion_completada" && data.generacion_id === generacionId) {
              finishWithResult();
            } else if (data.type === "generacion_error" && data.generacion_id === generacionId) {
              finishWithError(data.error || "Error en la generación");
            }
          } catch {
            // ignore parse errors
          }
        };
      })
      .catch(() => {
        // WS optional; polling handles progress
      });

    return () => {
      clearInterval(timer);
      clearInterval(stepTimer);
      clearInterval(pollInterval);
      clearTimeout(timeoutId);
      ws?.close();
    };
  }, [generacionId, router]);

  if (!generacionId) {
    return <div className="p-6 text-center">ID de generación no encontrado</div>;
  }

  if (error) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-white p-6">
        <div className="mb-4 text-4xl">❌</div>
        <h2 className="mb-2 text-xl font-semibold">Error en la generación</h2>
        <p className="mb-6 text-center text-gray-500">{error}</p>
        <button
          onClick={() => router.back()}
          className="rounded-xl bg-blue-600 px-6 py-3 font-semibold text-white hover:bg-blue-700"
        >
          Reintentar
        </button>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-white p-6">
      <div className="mb-8 h-16 w-16 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" />

      <div className="mb-2 text-center">
        <p className="text-2xl">{STEPS[currentStep].icon}</p>
        <h2 className="mt-2 text-lg font-semibold">{STEPS[currentStep].label}</h2>
      </div>

      <div className="mb-4 flex gap-2">
        {STEPS.map((_, i) => (
          <div
            key={i}
            className={`h-1.5 w-8 rounded-full transition-colors ${
              i <= currentStep ? "bg-blue-600" : "bg-gray-200"
            }`}
          />
        ))}
      </div>

      {elapsed > 90 && (
        <p className="animate-pulse text-sm text-gray-500">
          Tomando más tiempo de lo usual, casi listo...
        </p>
      )}

      <p className="mt-4 text-xs text-gray-400">{elapsed}s</p>
    </div>
  );
}

export default function ProgressPage() {
  return (
    <Suspense fallback={<div className="p-6 text-center">Cargando...</div>}>
      <ProgressScreen />
    </Suspense>
  );
}
