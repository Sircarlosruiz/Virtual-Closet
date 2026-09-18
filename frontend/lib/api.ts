export const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'http://localhost:8000';

export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

function messageFromDetail(detail: unknown, status: number): { message: string; code?: string } {
  if (typeof detail === 'string') {
    return { message: detail };
  }
  if (Array.isArray(detail)) {
    return {
      message: detail.map((entry: { msg?: string }) => entry.msg ?? 'Dato inválido').join('. '),
    };
  }
  if (detail && typeof detail === 'object') {
    const record = detail as { message?: string; code?: string };
    return {
      message: record.message ?? `HTTP ${status}`,
      code: record.code,
    };
  }
  return { message: `HTTP ${status}` };
}

export async function apiFetch(path: string, options: RequestInit = {}) {
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
  const response = await fetch(`${BACKEND_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers: isFormData
      ? { ...options.headers }
      : {
          'Content-Type': 'application/json',
          ...options.headers,
        },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Error desconocido' }));
    const parsed = messageFromDetail(error.detail, response.status);
    throw new ApiError(parsed.message, response.status, parsed.code);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}
