"use client";

import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import Link from "next/link";

import { apiFetch } from "@/lib/api";

const loginSchema = z.object({
  email: z.string().min(1, "El correo es obligatorio").email("Email inválido"),
  password: z.string().min(1, "La contraseña es obligatoria"),
});

type LoginForm = z.infer<typeof loginSchema>;

function LoginFormContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirect = searchParams.get("redirect");
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginForm) => {
    setIsLoading(true);
    try {
      const result = await apiFetch("/api/auth/login", {
        method: "POST",
        body: JSON.stringify(data),
      }) as { challenge_token?: string; requires_2fa_setup?: boolean; requires_2fa?: boolean; email?: string };

      // Store challenge_token in sessionStorage for 2FA flows
      if (result?.challenge_token) {
        sessionStorage.setItem("vc_challenge_token", result.challenge_token);
        if (result.email) {
          sessionStorage.setItem("vc_challenge_email", result.email);
        }
      }

      // Backend returns challenge_token + requires_2fa_setup for first-time 2FA
      // or requires_2fa for returning users who need to complete 2FA challenge
      if (result?.requires_2fa_setup) {
        router.push("/auth/2fa/setup");
      } else if (result?.requires_2fa) {
        router.push("/auth/2fa/challenge");
      } else {
        router.push(redirect || "/dashboard");
      }
      router.refresh();
    } catch (error) {
      if (error instanceof Error) {
        const msg = error.message;
        if (msg.includes("401") || msg.includes("incorrectos")) {
          toast.error("Email o contraseña incorrectos");
        } else if (msg.includes("423") || msg.includes("bloqueada")) {
          toast.error("Cuenta bloqueada. Revisá tu email para instrucciones de desbloqueo.");
        } else if (msg.includes("403") || msg.includes("verificar")) {
          toast.error("Debes verificar tu email antes de iniciar sesión.");
        } else {
          toast.error("Error de conexión. Intentá de nuevo.");
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

  return (
    <>
      <h1 className="text-2xl font-extrabold tracking-tight mb-1 text-gray-900">
        Bienvenida de vuelta
      </h1>
      <p className="text-sm mb-7 text-gray-500">
        Entrá para gestionar tus prendas y catálogos.
      </p>

      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
        {/* Email */}
        <div className="flex flex-col gap-1.5">
          <label htmlFor="email" className="text-sm font-semibold text-gray-800">
            Correo
          </label>
          <input
            id="email"
            type="email"
            placeholder="karla@boutique.ni"
            className={inputClass}
            style={{ borderColor: errors.email ? "#EF4444" : "#E5E7EB" }}
            {...register("email")}
          />
          {errors.email && (
            <p className="text-xs text-red-500">{errors.email.message}</p>
          )}
        </div>

        {/* Password */}
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <label htmlFor="password" className="text-sm font-semibold text-gray-800">
              Contraseña
            </label>
            <Link
              href="/auth/forgot-password"
              className="text-xs font-semibold text-indigo-600 hover:text-indigo-700"
            >
              ¿Olvidaste?
            </Link>
          </div>
          <input
            id="password"
            type="password"
            placeholder="••••••••"
            className={inputClass}
            style={{ borderColor: errors.password ? "#EF4444" : "#E5E7EB" }}
            {...register("password")}
          />
          {errors.password && (
            <p className="text-xs text-red-500">{errors.password.message}</p>
          )}
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={isLoading}
          className="mt-1 h-12 w-full rounded-full text-base font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
          style={{ background: "#6366F1", boxShadow: "0 4px 14px rgba(99,102,241,.32)" }}
        >
          {isLoading ? "Iniciando sesión..." : "Iniciar sesión"}
        </button>
      </form>

      {/* Divider */}
      <div className="my-6 flex items-center gap-3">
        <div className="h-px flex-1 bg-gray-200" />
        <span className="text-xs text-gray-400">o</span>
        <div className="h-px flex-1 bg-gray-200" />
      </div>

      {/* Google OAuth button (placeholder — NextAuth integration in next bolt) */}
      <button
        type="button"
        className="h-12 w-full rounded-full text-base font-semibold border border-gray-300 text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50"
        disabled
        title="Disponible próximamente"
      >
        Continuar con Google
      </button>

      <p className="mt-6 text-center text-sm text-gray-500">
        ¿No tenés cuenta?{" "}
        <Link href="/registro" className="font-semibold text-indigo-600 hover:text-indigo-700">
          Creá una gratis
        </Link>
      </p>
    </>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="py-12 text-center text-gray-500">Cargando...</div>}>
      <LoginFormContent />
    </Suspense>
  );
}
