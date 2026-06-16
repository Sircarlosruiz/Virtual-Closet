"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import Link from "next/link";

import { apiFetch } from "@/lib/api";

const resetSchema = z.object({
  new_password: z
    .string()
    .min(8, "La contraseña debe tener al menos 8 caracteres")
    .regex(/[A-Z]/, "Debe incluir al menos una mayúscula")
    .regex(/[0-9]/, "Debe incluir al menos un número"),
  confirm_password: z.string().min(1, "Debes confirmar la contraseña"),
}).refine((data) => data.new_password === data.confirm_password, {
  message: "Las contraseñas no coinciden",
  path: ["confirm_password"],
});

type ResetForm = z.infer<typeof resetSchema>;

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [isLoading, setIsLoading] = useState(false);
  const [tokenValid, setTokenValid] = useState<boolean | null>(null);
  const [resetSuccess, setResetSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetForm>({
    resolver: zodResolver(resetSchema),
  });

  // Pre-flight token validation
  useEffect(() => {
    if (!token) {
      setTokenValid(false);
      return;
    }
    // We can't validate the token without sending it, so we just check presence
    setTokenValid(true);
  }, [token]);

  const onSubmit = async (data: ResetForm) => {
    if (!token) return;

    setIsLoading(true);
    try {
      await apiFetch("/api/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({
          token,
          new_password: data.new_password,
        }),
      });
      setResetSuccess(true);
      toast.success("Contraseña actualizada exitosamente");
      setTimeout(() => {
        router.push("/login");
      }, 3000);
    } catch (error) {
      if (error instanceof Error) {
        const msg = error.message;
        if (msg.includes("expired") || msg.includes("expirado")) {
          toast.error("Este enlace ha expirado. Solicitá uno nuevo.");
        } else if (msg.includes("used") || msg.includes("utilizado")) {
          toast.error("Este enlace ya fue utilizado. Solicitá uno nuevo.");
        } else {
          toast.error("No se pudo restablecer la contraseña. Intentá de nuevo.");
        }
      }
    } finally {
      setIsLoading(false);
    }
  };

  const inputClass =
    "h-12 w-full rounded-xl border px-4 text-base outline-none transition-all " +
    "focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 " +
    "placeholder:text-gray-400";

  // No token — redirect to forgot-password
  if (tokenValid === false) {
    return (
      <>
        <h1 className="text-2xl font-extrabold tracking-tight mb-1 text-gray-900">
          Enlace inválido
        </h1>
        <p className="text-sm mb-7 text-gray-500">
          No se encontró un token de restablecimiento. Solicitá un nuevo enlace.
        </p>
        <Link
          href="/auth/forgot-password"
          className="h-12 w-full flex items-center justify-center rounded-full text-base font-semibold text-white transition-colors hover:bg-indigo-700"
          style={{ background: "#6366F1", boxShadow: "0 4px 14px rgba(99,102,241,.32)" }}
        >
          Solicitar nuevo enlace
        </Link>
      </>
    );
  }

  // Reset success
  if (resetSuccess) {
    return (
      <>
        <h1 className="text-2xl font-extrabold tracking-tight mb-1 text-green-700">
          Contraseña actualizada
        </h1>
        <p className="text-sm mb-7 text-gray-500">
          Tu contraseña ha sido actualizada. Serás redirigido al inicio de sesión en unos segundos.
        </p>
        <div className="rounded-xl border border-green-100 bg-green-50 p-4 mb-6">
          <p className="text-sm text-green-700">
            ✅ Contraseña actualizada. Redirigiendo…
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
      <h1 className="text-2xl font-extrabold tracking-tight mb-1 text-gray-900">
        Nueva contraseña
      </h1>
      <p className="text-sm mb-7 text-gray-500">
        Ingresá tu nueva contraseña.
      </p>

      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="new_password" className="text-sm font-semibold text-gray-800">
            Nueva contraseña
          </label>
          <input
            id="new_password"
            type="password"
            placeholder="Mínimo 8 caracteres"
            className={inputClass}
            style={{ borderColor: errors.new_password ? "#EF4444" : "#E5E7EB" }}
            {...register("new_password")}
          />
          <span className="text-xs text-gray-400">
            8+ caracteres, una mayúscula y un número.
          </span>
          {errors.new_password && (
            <p className="text-xs text-red-500">{errors.new_password.message}</p>
          )}
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="confirm_password" className="text-sm font-semibold text-gray-800">
            Confirmar contraseña
          </label>
          <input
            id="confirm_password"
            type="password"
            placeholder="Repetí tu nueva contraseña"
            className={inputClass}
            style={{ borderColor: errors.confirm_password ? "#EF4444" : "#E5E7EB" }}
            {...register("confirm_password")}
          />
          {errors.confirm_password && (
            <p className="text-xs text-red-500">{errors.confirm_password.message}</p>
          )}
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="mt-1 h-12 w-full rounded-full text-base font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
          style={{ background: "#6366F1", boxShadow: "0 4px 14px rgba(99,102,241,.32)" }}
        >
          {isLoading ? "Actualizando..." : "Actualizar contraseña"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-gray-500">
        <Link href="/login" className="font-semibold text-indigo-600 hover:text-indigo-700">
          Volver al inicio de sesión
        </Link>
      </p>
    </>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="py-12 text-center text-gray-500">Cargando...</div>}>
      <ResetPasswordForm />
    </Suspense>
  );
}
