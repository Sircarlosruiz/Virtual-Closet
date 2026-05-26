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

function extensionFromFile(file: File): "jpg" | "png" | "heic" {
  const fromName = file.name.split(".").pop()?.toLowerCase();
  if (fromName === "jpeg") return "jpg";
  if (fromName === "jpg" || fromName === "png" || fromName === "heic") {
    return fromName;
  }
  const mime = file.type.split(";", 1)[0].toLowerCase();
  if (mime === "image/jpeg") return "jpg";
  if (mime === "image/png") return "png";
  if (mime === "image/heic" || mime === "image/heif") return "heic";
  return "jpg";
}

function putFileWithProgress(
  uploadUrl: string,
  file: File,
  onProgress?: (percent: number) => void
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", uploadUrl, true);
    xhr.setRequestHeader("Content-Type", file.type || "image/jpeg");

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress((e.loaded / e.total) * 100);
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve();
        return;
      }
      reject(
        new Error(
          xhr.status === 0
            ? "No se pudo guardar en MinIO. Comprueba que esté en marcha (make docker-infra)."
            : `Error al guardar la imagen (HTTP ${xhr.status})`
        )
      );
    });

    xhr.addEventListener("error", () => {
      reject(
        new Error(
          "Error de red al guardar en MinIO. Ejecuta make docker-infra y vuelve a intentar."
        )
      );
    });

    xhr.send(file);
  });
}

/** Presigned URL upload (same flow as modelos IA) — reliable with auth cookies. */
export async function subirPrenda(
  file: File,
  nombre?: string,
  onProgress?: (percent: number) => void
): Promise<PrendaResponse> {
  const extension = extensionFromFile(file);
  const { upload_url, prenda_id, object_key } = await getUploadUrl(extension);
  await putFileWithProgress(upload_url, file, onProgress);
  return confirmarSubida({
    prenda_id,
    object_key,
    nombre: nombre || undefined,
  });
}

/** Direct multipart upload to the API (fallback). */
export async function subirPrendaDirecta(
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
              : xhr.status === 401
                ? "Sesión expirada. Vuelve a iniciar sesión."
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
