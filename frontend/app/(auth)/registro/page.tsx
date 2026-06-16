"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import Link from "next/link";

import { apiFetch } from "@/lib/api";

const registerSchema = z.object({
  email: z.string().min(1, "El correo es obligatorio").email("Email inválido"),
  password: z
    .string()
    .min(8, "La contraseña debe tener al menos 8 caracteres")
    .regex(/[A-Z]/, "Debe incluir al menos una mayúscula")
    .regex(/[0-9]/, "Debe incluir al menos un número"),
  password_confirm: z.string().min(1, "Debes confirmar la contraseña"),
  nombre_negocio: z.string().min(1, "El nombre del negocio es obligatorio"),
}).refine((data) => data.password === data.password_confirm, {
  message: "Las contraseñas no coinciden",
  path: ["password_confirm"],
});

type RegisterForm = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [registeredEmail, setRegisteredEmail] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterForm) => {
    setIsLoading(true);
    try {
      await apiFetch("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({
          email: data.email,
          password: data.password,
          business_name: data.nombre_negocio,
        }),
      });
      setRegisteredEmail(data.email);
    } catch (error) {
      if (error instanceof Error) {
        if (error.message.includes("409")) {
          toast.error("Este email ya está registrado");
        } else {
          toast.error("No se pudo crear la cuenta. Intentá de nuevo.");
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

  // Confirmation screen after successful registration
  if (registeredEmail) {
    return (
      <>
        <h1 className="text-2xl font-extrabold tracking-tight mb-1 text-gray-900">
          Revisá tu correo
        </h1>
        <p className="text-sm mb-7 text-gray-500">
          Te enviamos un enlace de verificación a{" "}
          <span className="font-semibold text-gray-700">{registeredEmail}</span>.
          Hacé clic en el enlace para activar tu cuenta.
        </p>

        <div className="rounded-xl border border-indigo-100 bg-indigo-50 p-4 mb-6">
          <p className="text-sm text-indigo-700">
            ¿No recibiste el correo? Revisá tu carpeta de spam o solicitá un nuevo enlace.
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
        Creá tu cuenta
      </h1>
      <p className="text-sm mb-7 text-gray-500">
        30 días gratis en Plan Base · sin tarjeta.
      </p>

      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
        {/* Nombre del negocio */}
        <div className="flex flex-col gap-1.5">
          <label htmlFor="nombre_negocio" className="text-sm font-semibold text-gray-800">
            Nombre del negocio
          </label>
          <input
            id="nombre_negocio"
            type="text"
            placeholder="Boutique Karla"
            className={inputClass}
            style={{ borderColor: errors.nombre_negocio ? "#EF4444" : "#E5E7EB" }}
            {...register("nombre_negocio")}
          />
          {errors.nombre_negocio && (
            <p className="text-xs text-red-500">{errors.nombre_negocio.message}</p>
          )}
        </div>

        {/* Correo */}
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

        {/* Contraseña */}
        <div className="flex flex-col gap-1.5">
          <label htmlFor="password" className="text-sm font-semibold text-gray-800">
            Contraseña
          </label>
          <input
            id="password"
            type="password"
            placeholder="Mínimo 8 caracteres"
            className={inputClass}
            style={{ borderColor: errors.password ? "#EF4444" : "#E5E7EB" }}
            {...register("password")}
          />
          <span className="text-xs text-gray-400">
            8+ caracteres, una mayúscula y un número.
          </span>
          {errors.password && (
            <p className="text-xs text-red-500">{errors.password.message}</p>
          )}
        </div>

        {/* Confirmar contraseña */}
        <div className="flex flex-col gap-1.5">
          <label htmlFor="password_confirm" className="text-sm font-semibold text-gray-800">
            Confirmar contraseña
          </label>
          <input
            id="password_confirm"
            type="password"
            placeholder="Repetí tu contraseña"
            className={inputClass}
            style={{ borderColor: errors.password_confirm ? "#EF4444" : "#E5E7EB" }}
            {...register("password_confirm")}
          />
          {errors.password_confirm && (
            <p className="text-xs text-red-500">{errors.password_confirm.message}</p>
          )}
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={isLoading}
          className="mt-1 h-12 w-full rounded-full text-base font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
          style={{ background: "#6366F1", boxShadow: "0 4px 14px rgba(99,102,241,.32)" }}
        >
          {isLoading ? "Creando cuenta..." : "Crear cuenta gratis"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-gray-500">
        ¿Ya tenés cuenta?{" "}
        <Link href="/login" className="font-semibold text-indigo-600 hover:text-indigo-700">
          Iniciá sesión
        </Link>
      </p>

      <p className="mt-3 text-center text-xs text-gray-400">
        Al crear tu cuenta aceptás los Términos y la Política de privacidad.
      </p>
    </>
  );
}
