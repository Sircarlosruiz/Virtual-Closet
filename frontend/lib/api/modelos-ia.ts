import { apiFetch } from "@/lib/api";

export interface ModeloIA {
  id: string;
  nombre: string;
  descripcion: string | null;
  thumbnail_url: string;
  plan_minimo: string;
}

export async function fetchModelosIA(): Promise<ModeloIA[]> {
  return apiFetch("/api/modelos-ia");
}
