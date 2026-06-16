"use client";

import { useTenant } from "@/hooks/useSettings";
import { AdminList } from "@/components/settings/admin-list";
import { Loader2, Building2 } from "lucide-react";

export default function AccountSettingsPage() {
  const { data: tenant, isLoading } = useTenant();

  return (
    <div className="space-y-8">
      {/* Business info */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-zinc-900">Información del negocio</h2>

        {isLoading ? (
          <div className="flex items-center gap-2 text-zinc-500">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-sm">Cargando...</span>
          </div>
        ) : tenant ? (
          <div className="flex items-center gap-3 p-4 bg-zinc-50 rounded-xl border">
            <Building2 className="h-5 w-5 text-zinc-400" />
            <div>
              <p className="font-medium text-zinc-900">{tenant.name}</p>
              <p className="text-sm text-zinc-500">/{tenant.slug}</p>
            </div>
          </div>
        ) : null}
      </div>

      {/* Admin management */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-zinc-900">Administradores</h2>
        <AdminList />
      </div>
    </div>
  );
}
