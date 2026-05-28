"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useRequestMagicLink } from "@/hooks/usePortal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const formSchema = z.object({
  email: z.string().email("Email inválido"),
});

type FormValues = z.infer<typeof formSchema>;

export default function RequestLinkPage() {
  const [submitted, setSubmitted] = useState(false);
  const requestMutation = useRequestMagicLink();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { email: "" },
  });

  const onSubmit = (values: FormValues) => {
    requestMutation.mutate(values, {
      onSuccess: () => setSubmitted(true),
    });
  };

  if (submitted) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center max-w-md">
          <p className="text-lg font-medium text-zinc-900 dark:text-zinc-50">
            Revisa tu correo
          </p>
          <p className="mt-2 text-zinc-600 dark:text-zinc-400">
            Si existe una cuenta con ese email, recibirás un nuevo enlace de acceso.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="w-full max-w-md">
        <div className="text-center mb-6">
          <p className="text-lg font-medium text-zinc-900 dark:text-zinc-50">
            Solicitar nuevo enlace
          </p>
          <p className="mt-2 text-zinc-600 dark:text-zinc-400">
            Ingresa tu email para recibir un nuevo enlace de acceso.
          </p>
        </div>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" placeholder="tu@email.com" {...register("email")} />
            {errors.email && (
              <p className="text-sm text-red-500">{errors.email.message}</p>
            )}
          </div>
          <Button type="submit" className="w-full" disabled={requestMutation.isPending}>
            {requestMutation.isPending ? "Enviando..." : "Enviar enlace"}
          </Button>
        </form>
      </div>
    </div>
  );
}
