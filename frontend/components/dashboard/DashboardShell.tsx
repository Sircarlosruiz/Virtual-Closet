"use client";

import { AppSidebar } from "@/components/dashboard/AppSidebar";
import { DashboardPageContainer } from "@/components/dashboard/DashboardPageContainer";
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
      <SidebarInset className="min-w-0">
        <DashboardTopBar user={user} />
        <div className="flex w-full min-w-0 flex-1 flex-col">
          <DashboardPageContainer>{children}</DashboardPageContainer>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
