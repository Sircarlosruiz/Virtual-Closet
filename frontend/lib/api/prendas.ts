import { apiFetch } from "@/lib/api";

export type UploadUrlResponse = {
  upload_url: string;
  prenda_id: string;
  object_key: string;
};

export type PrendaResponse = {
  id: string;
  nombre: string;
  imagen_original_url: string;
  estado: string;
  created_at: string;
};

export type PrendasListResponse = {
  items: PrendaResponse[];
  next_cursor: string | null;
};

export type ConfirmarSubidaInput = {
  prenda_id: string;
  object_key: string;
  nombre?: string;
};

export function normalizeUploadExtension(ext: string): "jpg" | "png" | "heic" {
  const normalized = ext === "jpeg" ? "jpg" : ext;
  if (normalized === "jpg" || normalized === "png" || normalized === "heic") {
    return normalized;
  }
  return "jpg";
}

export async function getUploadUrl(
  extension: "jpg" | "png" | "heic" | "jpeg"
): Promise<UploadUrlResponse> {
  const ext = normalizeUploadExtension(extension);
  return apiFetch(`/api/prendas/upload-url?extension=${ext}`);
}

export async function confirmarSubida(
  data: ConfirmarSubidaInput
): Promise<PrendaResponse> {
  return apiFetch("/api/prendas", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getPrendas(cursor?: string): Promise<PrendasListResponse> {
  const params = cursor ? `?cursor=${cursor}` : "";
  return apiFetch(`/api/prendas${params}`);
}

export async function updateNombre(
  id: string,
  nombre: string
): Promise<PrendaResponse> {
  return apiFetch(`/api/prendas/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ nombre }),
  });
}

export async function deletePrenda(id: string): Promise<void> {
  return apiFetch(`/api/prendas/${id}`, { method: "DELETE" });
}
