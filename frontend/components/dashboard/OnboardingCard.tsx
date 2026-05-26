import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function OnboardingCard() {
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-md text-center">
        <CardHeader>
          <CardTitle className="text-2xl">Bienvenido a Virtual Closet</CardTitle>
          <CardDescription>
            30 días gratis en Plan Base, sin tarjeta — hasta 40 prendas al mes
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Transforma fotos planas de tus prendas en catálogos profesionales con IA.
            Comienza ahora subiendo tu primera prenda.
          </p>
          <Link href="/dashboard/prendas/nueva" className="block">
            <Button size="lg" className="w-full">
              Subir tu primera prenda
            </Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
