const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

export async function apiFetch(path: string, options: RequestInit = {}) {
  const response = await fetch(`${BACKEND_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Error desconocido" }));
    const detail = error.detail;
    let message: string;
    if (typeof detail === "string") {
      message = detail;
    } else if (Array.isArray(detail)) {
      message = detail.map((e: { msg?: string }) => e.msg ?? "Dato inválido").join(". ");
    } else {
      message = `HTTP ${response.status}`;
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}
