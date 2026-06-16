"use client";

import { useEffect, useState, useCallback, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import Link from "next/link";

import { apiFetch } from "@/lib/api";

function VerifyEmailContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [status, setStatus] = useState<"verifying" | "success" | "error">("verifying");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const verify = useCallback(async () => {
    if (!token) {
      setStatus("error");
      setErrorMessage("No se proporcionó un token de verificación.");
      return;
    }

    try {
      await apiFetch(`/api/auth/verify-email?token=${token}`);
      setStatus("success");
      toast.success("Email verificado exitosamente");
      setTimeout(() => {
        router.push("/login");
      }, 3000);
    } catch {
      setStatus("error");
      setErrorMessage("El enlace es inválido o ya fue utilizado.");
    }
  }, [token, router]);

  useEffect(() => {
    verify();
  }, [verify]);

  const handleResend = async () => {
    const email = prompt("Ingresá tu email para reenviar el enlace:");
    if (!email) return;

    try {
      await apiFetch("/api/auth/resend-verification", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      toast.success("Si el email existe, se envió un nuevo enlace");
    } catch {
      toast.error("No se pudo reenviar el enlace. Intentá de nuevo.");
    }
  };

  if (status === "verifying") {
    return (
      <>
        <h1 className="text-2xl font-extrabold tracking-tight mb-1 text-gray-900">
          Verificando email
        </h1>
        <p className="text-sm mb-7 text-gray-500">
          Estamos confirmando tu dirección de correo…
        </p>
        <div className="flex flex-col items-center justify-center py-8">
          <div
            className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-200 border-t-indigo-600"
          />
        </div>
      </>
    );
  }

  if (status === "success") {
    return (
      <>
        <h1 className="text-2xl font-extrabold tracking-tight mb-1 text-green-700">
          Email verificado
        </h1>
        <p className="text-sm mb-7 text-gray-500">
          Tu cuenta ha sido activada. Serás redirigido al inicio de sesión en unos segundos.
        </p>
        <div className="rounded-xl border border-green-100 bg-green-50 p-4 mb-6">
          <p className="text-sm text-green-700">
            ✅ Verificación exitosa. Redirigiendo…
          </p>
        </div>
        <p className="text-center text-sm text-gray-500">
          <Link href="/login" className="font-semibold text-indigo-600 hover:text-indigo-700">
            Ir al inicio de sesión
          </Link>
        </p>
      </>
    );
  }

  return (
    <>
      <h1 className="text-2xl font-extrabold tracking-tight mb-1 text-red-700">
        Enlace inválido
      </h1>
      <p className="text-sm mb-7 text-gray-500">
        {errorMessage}
      </p>
      <div className="rounded-xl border border-red-100 bg-red-50 p-4 mb-6">
        <p className="text-sm text-red-700">
          Este enlace de verificación ha expirado o ya fue utilizado.
        </p>
      </div>
      <button
        onClick={handleResend}
        className="h-12 w-full rounded-full text-base font-semibold text-white transition-colors hover:bg-indigo-700"
        style={{ background: "#6366F1", boxShadow: "0 4px 14px rgba(99,102,241,.32)" }}
      >
        Reenviar enlace de verificación
      </button>
      <p className="mt-6 text-center text-sm text-gray-500">
        <Link href="/login" className="font-semibold text-indigo-600 hover:text-indigo-700">
          Volver al inicio de sesión
        </Link>
      </p>
    </>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<div className="py-12 text-center text-gray-500">Cargando...</div>}>
      <VerifyEmailContent />
    </Suspense>
  );
}
