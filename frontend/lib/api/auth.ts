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

export interface LoginResponse {
  challenge_token: string;
  requires_2fa_setup: boolean;
}

export async function fetchMe(): Promise<MayoristaProfile> {
  return apiFetch("/api/auth/me");
}

export async function login(
  email: string,
  password: string,
): Promise<LoginResponse> {
  return apiFetch("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function logout(): Promise<void> {
  await apiFetch("/api/auth/logout", { method: "POST" });
}

export async function logoutAll(): Promise<{ revoked_count: number }> {
  return apiFetch("/api/auth/logout-all", { method: "POST" });
}

export async function refreshToken(): Promise<{ token_type: string; expires_in: number }> {
  return apiFetch("/api/auth/refresh", { method: "POST" });
}

export async function forgotPassword(email: string): Promise<void> {
  await apiFetch("/api/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function resetPassword(
  token: string,
  new_password: string,
): Promise<void> {
  await apiFetch("/api/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({ token, new_password }),
  });
}

export async function verifyEmail(token: string): Promise<void> {
  await apiFetch(`/api/auth/verify-email?token=${token}`);
}

export async function resendVerification(email: string): Promise<void> {
  await apiFetch("/api/auth/resend-verification", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}
