"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

function PortalAuthScreen() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [error, setError] = useState<string>("");

  useEffect(() => {
    const token = searchParams.get("token");
    if (!token) {
      setStatus("error");
      setError("Token no proporcionado");
      return;
    }

    apiFetch(`/api/portal/auth?token=${token}`)
      .then(() => {
        setStatus("success");
        router.push("/portal");
      })
      .catch((err) => {
        setStatus("error");
        setError(err.message || "Token inválido o expirado");
      });
  }, [searchParams, router]);

  if (status === "loading") {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-zinc-900 dark:border-zinc-100 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="mt-4 text-zinc-600 dark:text-zinc-400">
            Validando tu acceso...
          </p>
        </div>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center max-w-md">
          <p className="text-lg font-medium text-red-600">{error}</p>
          <p className="mt-2 text-zinc-600 dark:text-zinc-400">
            Tu enlace puede haber expirado. Solicita un nuevo enlace.
          </p>
          <button
            onClick={() => router.push("/portal/request-link")}
            className="mt-4 px-4 py-2 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 rounded-lg hover:opacity-90 transition-opacity"
          >
            Solicitar nuevo enlace
          </button>
        </div>
      </div>
    );
  }

  return null;
}

export default function PortalAuthPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center">
            <div className="w-8 h-8 border-2 border-zinc-900 dark:border-zinc-100 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="mt-4 text-zinc-600 dark:text-zinc-400">Cargando...</p>
          </div>
        </div>
      }
    >
      <PortalAuthScreen />
    </Suspense>
  );
}
