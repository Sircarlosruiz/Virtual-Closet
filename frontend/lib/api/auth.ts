import { apiFetch } from "@/lib/api";

export interface MayoristaProfile {
  id: string;
  email: string;
  nombre_negocio: string;
  plan: string;
  trial_activo: boolean;
  trial_expira_en: string;
  prendas_count: number;
}

export async function fetchMe(): Promise<MayoristaProfile> {
  return apiFetch("/api/auth/me");
}

export async function logout(): Promise<void> {
  await apiFetch("/api/auth/logout", { method: "POST" });
}
