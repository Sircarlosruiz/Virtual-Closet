"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { BuyerAccessValidator } from "@/components/portal/buyer-access-validator";

function AccessContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  if (!token) {
    return (
      <div className="max-w-6xl mx-auto py-8 px-4">
        <div className="text-center py-12">
          <h2 className="text-xl font-semibold text-zinc-900 mb-2">
            Sin token de acceso
          </h2>
          <p className="text-sm text-zinc-500 mb-6">
            Este enlace no contiene un token válido. Contactá al mayorista para recibir acceso.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto py-8 px-4">
      <BuyerAccessValidator token={token} />
    </div>
  );
}

export default function PortalAccessPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-6xl mx-auto py-8 px-4">
          <div className="flex flex-col items-center justify-center py-16">
            <div className="h-8 w-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
            <p className="text-sm text-zinc-500 mt-4">Cargando...</p>
          </div>
        </div>
      }
    >
      <AccessContent />
    </Suspense>
  );
}
