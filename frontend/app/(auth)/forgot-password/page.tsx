"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import Link from "next/link";

import { apiFetch } from "@/lib/api";

const forgotSchema = z.object({
  email: z.string().min(1, "El correo es obligatorio").email("Email inválido"),
});

type ForgotForm = z.infer<typeof forgotSchema>;

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotForm>({
    resolver: zodResolver(forgotSchema),
  });

  const onSubmit = async (data: ForgotForm) => {
    setIsLoading(true);
    try {
      await apiFetch("/api/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify(data),
      });
      // Always show success (no enumeration)
      setSubmitted(true);
    } catch {
      // Still show success (no enumeration)
      setSubmitted(true);
    } finally {
      setIsLoading(false);
    }
  };

  const inputClass =
    "h-12 w-full rounded-xl border px-4 text-base outline-none transition-all " +
    "focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 " +
    "placeholder:text-gray-400";

  if (submitted) {
    return (
      <>
        <h1 className="text-2xl font-extrabold tracking-tight mb-1 text-gray-900">
          Revisá tu correo
        </h1>
        <p className="text-sm mb-7 text-gray-500">
          Si ese email está registrado, recibirás un enlace para restablecer tu contraseña.
        </p>
        <div className="rounded-xl border border-indigo-100 bg-indigo-50 p-4 mb-6">
          <p className="text-sm text-indigo-700">
            El enlace expira en 1 hora. Si no lo ves, revisá tu carpeta de spam.
          </p>
        </div>
        <p className="text-center text-sm text-gray-500">
          <Link href="/login" className="font-semibold text-indigo-600 hover:text-indigo-700">
            Volver al inicio de sesión
          </Link>
        </p>
      </>
    );
  }

  return (
    <>
      <h1 className="text-2xl font-extrabold tracking-tight mb-1 text-gray-900">
        ¿Olvidaste tu contraseña?
      </h1>
      <p className="text-sm mb-7 text-gray-500">
        Ingresá tu email y te enviaremos un enlace para restablecerla.
      </p>

      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
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

        <button
          type="submit"
          disabled={isLoading}
          className="mt-1 h-12 w-full rounded-full text-base font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
          style={{ background: "#6366F1", boxShadow: "0 4px 14px rgba(99,102,241,.32)" }}
        >
          {isLoading ? "Enviando..." : "Enviar enlace"}
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
