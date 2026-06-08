import { BookOpen, Shirt, Users, type LucideIcon } from "lucide-react";

export interface DashboardNavItem {
  title: string;
  href: string;
  icon: LucideIcon;
}

export const dashboardNavItems: DashboardNavItem[] = [
  {
    title: "Mis prendas",
    href: "/dashboard",
    icon: Shirt,
  },
  {
    title: "Catálogos",
    href: "/dashboard/catalogos",
    icon: BookOpen,
  },
  {
    title: "Clientes",
    href: "/dashboard/customers",
    icon: Users,
  },
];

export function isDashboardNavActive(pathname: string, href: string): boolean {
  if (href === "/dashboard") {
    return pathname === "/dashboard" || pathname === "/dashboard/onboarding";
  }

  return pathname === href || pathname.startsWith(`${href}/`);
}

export function getDashboardPageTitle(pathname: string): string {
  if (pathname === "/dashboard" || pathname === "/dashboard/onboarding") {
    return "Mis prendas";
  }

  if (pathname.startsWith("/dashboard/prendas/nueva")) {
    return "Nueva prenda";
  }

  if (pathname === "/dashboard/catalogos") {
    return "Catálogos";
  }

  if (pathname.startsWith("/dashboard/catalogos/agregar")) {
    return "Agregar al catálogo";
  }

  if (/^\/dashboard\/catalogos\/[^/]+$/.test(pathname)) {
    return "Detalle del catálogo";
  }

  if (pathname.startsWith("/dashboard/customers")) {
    return "Clientes";
  }

  if (pathname.includes("/generacion/model-selector")) {
    return "Seleccionar modelo";
  }

  if (pathname.includes("/generacion/progress")) {
    return "Generando imagen";
  }

  if (pathname.includes("/generacion/result")) {
    return "Resultado de generación";
  }

  if (pathname === "/extraction/new") {
    return "Extraer prendas";
  }

  if (pathname === "/extraction/status") {
    return "Estado de extracción";
  }

  if (pathname === "/media/extracted") {
    return "Prendas extraídas";
  }

  if (pathname === "/generate") {
    return "Generar prueba virtual";
  }

  if (pathname === "/jobs") {
    return "Historial de generaciones";
  }

  if (/^\/jobs\/[^/]+$/.test(pathname)) {
    return "Estado del trabajo";
  }

  if (pathname === "/batches") {
    return "Lotes";
  }

  if (pathname === "/batches/new") {
    return "Nuevo lote";
  }

  if (/^\/batches\/[^/]+$/.test(pathname)) {
    return "Detalle del lote";
  }

  return "Dashboard";
}
