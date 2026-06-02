"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
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

export default function LoginPage() {
  const router = useRouter();
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
      await apiFetch("/api/auth/login", {
        method: "POST",
        body: JSON.stringify(data),
      });
      toast.success("Bienvenido de vuelta");
      router.push("/dashboard");
      router.refresh();
    } catch (error) {
      if (error instanceof Error) {
        toast.error("Email o contraseña incorrectos");
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
            <span className="text-xs font-semibold text-indigo-600 cursor-pointer">
              ¿Olvidaste?
            </span>
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

      <p className="mt-6 text-center text-sm text-gray-500">
        ¿No tenés cuenta?{" "}
        <Link href="/registro" className="font-semibold text-indigo-600 hover:text-indigo-700">
          Creá una gratis
        </Link>
      </p>
    </>
  );
}
