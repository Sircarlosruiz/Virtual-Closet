import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import Link from "next/link";

export default function OnboardingPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 px-4 dark:bg-zinc-950">
      <Card className="w-full max-w-md text-center">
        <CardHeader>
          <CardTitle className="text-2xl">Bienvenido a Virtual Closet</CardTitle>
          <CardDescription>
            Tus primeras 5 prendas son gratis, sin tarjeta
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Transforma fotos planas de tus prendas en catálogos profesionales con IA.
            Comienza ahora subiendo tu primera prenda.
          </p>
          <Link href="/dashboard/nueva-prenda" className="block">
            <Button size="lg" className="w-full">
              Subir tu primera prenda
            </Button>
          </Link>
          <p className="text-xs text-zinc-500 dark:text-zinc-500">
            Próximamente: Épica 2 - Gestión de prendas
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
