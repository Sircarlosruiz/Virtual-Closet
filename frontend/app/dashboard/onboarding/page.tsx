import { redirect } from "next/navigation";
import { Button } from "@/components/ui/button";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

async function getPrendasCount(): Promise<number | null> {
  try {
    const { cookies } = await import("next/headers");
    const cookieStore = await cookies();
    const token = cookieStore.get("access_token")?.value;
    if (!token) return null;

    const res = await fetch(`${BACKEND_URL}/api/auth/me`, {
      headers: { Cookie: `access_token=${token}` },
      cache: "no-store",
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data.prendas_count ?? 0;
  } catch {
    return null;
  }
}
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import Link from "next/link";

export default async function OnboardingPage() {
  const prendasCount = await getPrendasCount();
  if (prendasCount !== null && prendasCount > 0) {
    redirect("/dashboard");
  }

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
          <Link href="/dashboard/prendas/nueva" className="block">
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
