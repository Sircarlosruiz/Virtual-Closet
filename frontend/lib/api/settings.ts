import { apiFetch } from "@/lib/api";

export interface ValidateLinkResponse {
  valid: boolean;
  tenant_id?: string;
  catalog_ids?: string[];
  reason?: string;
}

export interface BuyerLinkRequest {
  catalog_ids: string[];
  ttl_days?: number;
}

export interface BuyerLinkResponse {
  id: string;
  tenant_id: string;
  catalog_ids: string[];
  signed_url: string;
  expires_at: string;
  created_at: string;
}

export interface BuyerLinkListResponse {
  links: BuyerLinkResponse[];
}

export interface AdminResponse {
  id: string;
  email: string;
  role: string;
  created_at: string;
}

export interface AdminListResponse {
  admins: AdminResponse[];
}

export interface AdminInviteRequest {
  email: string;
}

export interface TenantResponse {
  id: string;
  name: string;
  slug: string;
  settings: Record<string, unknown>;
}

export async function validateBuyerLink(token: string): Promise<ValidateLinkResponse> {
  return apiFetch("/api/buyer-links/validate", {
    method: "POST",
    body: JSON.stringify({ token }),
  }) as Promise<ValidateLinkResponse>;
}

export async function generateBuyerLink(
  body: BuyerLinkRequest
): Promise<BuyerLinkResponse> {
  return apiFetch("/api/tenants/buyer-links", {
    method: "POST",
    body: JSON.stringify(body),
  }) as Promise<BuyerLinkResponse>;
}

export async function listBuyerLinks(): Promise<BuyerLinkListResponse> {
  return apiFetch("/api/tenants/buyer-links") as Promise<BuyerLinkListResponse>;
}

export async function getTenant(): Promise<TenantResponse> {
  return apiFetch("/api/tenants/me") as Promise<TenantResponse>;
}

export async function listAdmins(): Promise<AdminListResponse> {
  return apiFetch("/api/tenants/admins") as Promise<AdminListResponse>;
}

export async function inviteAdmin(email: string): Promise<void> {
  await apiFetch("/api/tenants/admins/invite", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function revokeAdmin(adminId: string): Promise<void> {
  await apiFetch(`/api/tenants/admins/${adminId}`, {
    method: "DELETE",
  });
}
