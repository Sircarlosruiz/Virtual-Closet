import { apiFetch } from "@/lib/api";

export interface GeneracionResponse {
  id: string;
  prenda_id: string;
  modelo_ia_id: string;
  estado: string;
  imagen_url: string | null;
  thumbnail_url: string | null;
  costo_inferencia_usd: number | null;
  error_message: string | null;
  created_at: string;
}

export async function crearGeneracion(prenda_id: string, modelo_ia_id: string): Promise<GeneracionResponse> {
  return apiFetch("/api/generaciones", {
    method: "POST",
    body: JSON.stringify({ prenda_id, modelo_ia_id }),
  });
}

export async function fetchGeneracion(generacion_id: string): Promise<GeneracionResponse> {
  return apiFetch(`/api/generaciones/${generacion_id}`);
}

export async function fetchGeneracionesByPrenda(prenda_id: string): Promise<GeneracionResponse[]> {
  return apiFetch(`/api/prendas/${prenda_id}/generaciones`);
}
