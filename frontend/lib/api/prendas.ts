import { apiFetch, BACKEND_URL } from "@/lib/api";

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

export async function subirPrenda(
  file: File,
  nombre?: string,
  onProgress?: (percent: number) => void
): Promise<PrendaResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (nombre) {
    formData.append("nombre", nombre);
  }

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${BACKEND_URL}/api/prendas/upload`);
    xhr.withCredentials = true;

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress((e.loaded / e.total) * 100);
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch {
          reject(new Error("Respuesta inválida del servidor"));
        }
        return;
      }
      try {
        const err = JSON.parse(xhr.responseText);
        const detail = err.detail;
        const message =
          typeof detail === "string"
            ? detail
            : Array.isArray(detail)
              ? detail.map((d: { msg?: string }) => d.msg ?? "Dato inválido").join(". ")
              : `HTTP ${xhr.status}`;
        reject(new Error(message));
      } catch {
        reject(new Error(`HTTP ${xhr.status}`));
      }
    });

    xhr.addEventListener("error", () => {
      reject(new Error("Error de red al subir la prenda"));
    });

    xhr.send(formData);
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
