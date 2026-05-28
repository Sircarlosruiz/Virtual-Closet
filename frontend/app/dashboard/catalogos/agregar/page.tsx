"use client";

import { Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { AddGeneracionToCatalogForm } from "@/components/catalogos/AddGeneracionToCatalogForm";
import { Button } from "@/components/ui/button";

function AgregarAlCatalogoScreen() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const generacionId = searchParams.get("generacionId");

  if (!generacionId) {
    return (
      <div className="mx-auto max-w-lg p-6 text-center">
        <p className="text-muted-foreground">Falta el identificador de la generación.</p>
        <Button
          variant="outline"
          className="mt-4"
          onClick={() => router.push("/dashboard/catalogos")}
        >
          Ir a catálogos
        </Button>
      </div>
    );
  }

  return <AddGeneracionToCatalogForm generacionId={generacionId} />;
}

export default function AgregarAlCatalogoPage() {
  return (
    <Suspense fallback={<div className="p-6 text-center">Cargando...</div>}>
      <AgregarAlCatalogoScreen />
    </Suspense>
  );
}
