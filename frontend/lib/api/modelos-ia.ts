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

export async function getModeloUploadUrl(extension: string): Promise<{
  upload_url: string;
  modelo_id: string;
  object_key: string;
}> {
  return apiFetch(`/api/modelos-ia/upload-url?extension=${extension}`);
}

export async function crearModelo(data: {
  modelo_id: string;
  nombre: string;
  descripcion?: string;
  object_key: string;
}): Promise<ModeloIA> {
  return apiFetch("/api/modelos-ia", {
    method: "POST",
    body: JSON.stringify(data),
  });
}
