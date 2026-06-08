"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Shirt, BookOpen, Users, Plus, LogOut, Scissors, Wand2, Layers } from "lucide-react";

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { isDashboardNavActive } from "@/components/dashboard/dashboard-nav";
import type { MayoristaProfile } from "@/lib/api/auth";
import { logout } from "@/lib/api/auth";

interface AppSidebarProps {
  user: Pick<MayoristaProfile, "nombre_negocio" | "plan" | "trial_activo" | "email">;
}

const NAV_ITEMS = [
  { href: "/dashboard", icon: Shirt, label: "Mis prendas" },
  { href: "/dashboard/catalogos", icon: BookOpen, label: "Catálogos" },
  { href: "/dashboard/customers", icon: Users, label: "Clientes" },
];

const VTON_NAV_ITEMS = [
  { href: "/extraction/new", icon: Scissors, label: "Extracción" },
  { href: "/generate", icon: Wand2, label: "Generaciones" },
  { href: "/batches", icon: Layers, label: "Lotes" },
];

export function AppSidebar({ user }: AppSidebarProps) {
  const pathname = usePathname();
  const router = useRouter();

  const initials = user.nombre_negocio
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();

  const handleLogout = async () => {
    try {
      await logout();
    } finally {
      router.push("/login");
    }
  };

  return (
    <Sidebar collapsible="icon" variant="inset">
      {/* Brand header */}
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              size="lg"
              render={<Link href="/dashboard" />}
              tooltip="Virtual Closet"
            >
              <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-indigo-600 text-white">
                <Shirt className="size-4" />
              </div>
              <div className="grid flex-1 text-left text-sm leading-tight">
                <span className="truncate font-bold">Virtual Closet</span>
                <span className="truncate text-xs text-muted-foreground">
                  {user.nombre_negocio}
                </span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        {/* Main nav */}
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV_ITEMS.map((item) => (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton
                    render={<Link href={item.href} />}
                    isActive={isDashboardNavActive(pathname, item.href)}
                    tooltip={item.label}
                  >
                    <item.icon />
                    <span>{item.label}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* VTON nav */}
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {VTON_NAV_ITEMS.map((item) => (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton
                    render={<Link href={item.href} />}
                    isActive={isDashboardNavActive(pathname, item.href)}
                    tooltip={item.label}
                  >
                    <item.icon />
                    <span>{item.label}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Quick action */}
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  render={<Link href="/dashboard/prendas/nueva" />}
                  tooltip="Nueva prenda"
                >
                  <Plus />
                  <span>Nueva prenda</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Plan card */}
        <SidebarGroup className="mt-auto group-data-[collapsible=icon]:hidden">
          <SidebarGroupContent>
            <div
              className="mx-2 rounded-2xl p-4 text-white"
              style={{ background: "linear-gradient(135deg,#4F46E5,#6366F1 55%,#8B5CF6)" }}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-bold">Plan Base</span>
                <span
                  className="rounded-full px-2 py-0.5 text-xs font-semibold"
                  style={{ background: "rgba(255,255,255,.2)" }}
                >
                  {user.trial_activo ? "Prueba" : "Activo"}
                </span>
              </div>
              {user.trial_activo && (
                <div className="text-xs opacity-90 mt-0.5">22 días restantes</div>
              )}
              <div
                className="mt-3 h-1.5 rounded-full overflow-hidden"
                style={{ background: "rgba(255,255,255,.25)" }}
              >
                <div
                  className="h-full rounded-full"
                  style={{ width: "27%", background: "#fff" }}
                />
              </div>
            </div>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      {/* User footer */}
      <SidebarFooter>
        <div className="flex items-center gap-3 px-2 py-2 group-data-[collapsible=icon]:hidden">
          {/* Avatar */}
          <div
            className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold text-white"
            style={{ background: "#6366F1" }}
          >
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <div className="truncate text-xs font-bold text-sidebar-foreground">
              {user.nombre_negocio}
            </div>
            <div className="truncate text-xs text-muted-foreground">{user.email}</div>
          </div>
          {/* Logout */}
          <button
            onClick={handleLogout}
            aria-label="Salir"
            className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg transition-colors hover:bg-gray-100"
          >
            <LogOut className="h-4 w-4 text-muted-foreground" />
          </button>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
