import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-4 text-center">
      <h1 className="text-2xl font-semibold">Página no encontrada</h1>
      <p className="max-w-md text-muted-foreground">
        La ruta que buscas no existe o fue movida.
      </p>
      <div className="flex gap-3">
        <Link href="/">
          <Button variant="outline">Ir al inicio</Button>
        </Link>
        <Link href="/login">
          <Button>Iniciar sesión</Button>
        </Link>
      </div>
    </div>
  );
}
