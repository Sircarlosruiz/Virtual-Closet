import { apiFetch } from "@/lib/api";

export interface PortalCatalog {
  id: string;
  name: string;
  status: "published";
  item_count: number;
  created_at: string;
}

export interface PortalCatalogListResponse {
  catalogs: PortalCatalog[];
  total: number;
  page: number;
  page_size: number;
}

export interface PortalCatalogItem {
  id: string;
  image_url: string;
  garment_name: string;
  price: number | string;
  cloth_type: string;
  sku: string;
  position: number;
}

export interface PortalCatalogDetail extends PortalCatalog {
  items: PortalCatalogItem[];
}

export interface MagicLinkInput {
  email: string;
}

export async function getPortalCatalogs(
  page = 1,
  pageSize = 20
): Promise<PortalCatalogListResponse> {
  return apiFetch(`/api/portal/catalogs?page=${page}&page_size=${pageSize}`);
}

export async function getPortalCatalog(id: string): Promise<PortalCatalogDetail> {
  return apiFetch(`/api/portal/catalogs/${id}`);
}

export async function requestMagicLink(
  input: MagicLinkInput
): Promise<{ message: string }> {
  return apiFetch("/api/portal/magic-link", {
    method: "POST",
    body: JSON.stringify(input),
  });
}
