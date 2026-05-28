"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ChevronDown, LogOut } from "lucide-react";
import { toast } from "sonner";

import { getDashboardPageTitle } from "@/components/dashboard/dashboard-nav";
import { buttonVariants } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { logout } from "@/lib/api/auth";
import type { MayoristaProfile } from "@/lib/api/auth";
import { cn } from "@/lib/utils";

interface DashboardTopBarProps {
  user: Pick<MayoristaProfile, "nombre_negocio" | "email" | "plan" | "trial_activo">;
}

function getInitials(name: string): string {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

export function DashboardTopBar({ user }: DashboardTopBarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const title = getDashboardPageTitle(pathname);

  const handleLogout = async () => {
    try {
      await logout();
      router.push("/login");
      router.refresh();
    } catch {
      toast.error("No se pudo cerrar la sesión");
    }
  };

  return (
    <header className="sticky top-0 z-20 flex h-14 shrink-0 items-center gap-2 border-b bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <SidebarTrigger className="-ml-1" />
      <Separator orientation="vertical" className="mx-1 h-4" />
      <h1 className="truncate text-base font-semibold text-foreground">{title}</h1>

      <div className="ml-auto flex items-center gap-2">
        {pathname === "/dashboard" && (
          <Link
            href="/dashboard/prendas/nueva"
            className={cn(buttonVariants({ size: "sm" }))}
          >
            Nueva prenda
          </Link>
        )}

        <DropdownMenu>
          <DropdownMenuTrigger
            className={cn(
              buttonVariants({ variant: "outline", size: "sm" }),
              "gap-2 pl-2 pr-2"
            )}
          >
            <span className="flex size-6 items-center justify-center rounded-full bg-primary text-xs font-medium text-primary-foreground">
              {getInitials(user.nombre_negocio)}
            </span>
            <span className="hidden max-w-32 truncate sm:inline">
              {user.nombre_negocio}
            </span>
            <ChevronDown className="size-4 opacity-60" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuGroup>
              <DropdownMenuLabel className="font-normal">
                <div className="flex flex-col gap-1">
                  <span className="truncate font-medium">{user.nombre_negocio}</span>
                  <span className="truncate text-xs text-muted-foreground">{user.email}</span>
                </div>
              </DropdownMenuLabel>
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <DropdownMenuGroup>
              <DropdownMenuItem disabled>
                Plan {user.plan}
                {user.trial_activo ? " · Prueba activa" : ""}
              </DropdownMenuItem>
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <DropdownMenuGroup>
              <DropdownMenuItem onClick={handleLogout}>
                <LogOut className="size-4" />
                Cerrar sesión
              </DropdownMenuItem>
            </DropdownMenuGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
