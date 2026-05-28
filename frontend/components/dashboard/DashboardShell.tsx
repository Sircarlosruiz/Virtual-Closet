"use client";

import { AppSidebar } from "@/components/dashboard/AppSidebar";
import { DashboardTopBar } from "@/components/dashboard/DashboardTopBar";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import type { MayoristaProfile } from "@/lib/api/auth";

interface DashboardShellProps {
  user: Pick<MayoristaProfile, "nombre_negocio" | "email" | "plan" | "trial_activo">;
  children: React.ReactNode;
}

export function DashboardShell({ user, children }: DashboardShellProps) {
  return (
    <SidebarProvider>
      <AppSidebar user={user} />
      <SidebarInset>
        <DashboardTopBar user={user} />
        <div className="flex flex-1 flex-col">{children}</div>
      </SidebarInset>
    </SidebarProvider>
  );
}
