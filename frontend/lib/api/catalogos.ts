import { apiFetch } from "@/lib/api";

export interface Catalogo {
  id: string;
  name: string;
  status: "draft" | "published";
  item_count: number;
  created_at: string;
  updated_at: string;
}

export interface CatalogoListResponse {
  catalogs: Catalogo[];
  total: number;
  page: number;
  page_size: number;
}

export interface CatalogoItem {
  id: string;
  catalog_id: string;
  vton_job_id: string | null;
  generacion_id?: string | null;
  image_url: string;
  garment_name: string;
  price: number | string;
  cloth_type: "upper_body" | "lower_body" | "dress";
  sku: string;
  position: number;
  created_at: string;
}

export interface CatalogoDetail extends Catalogo {
  items: CatalogoItem[];
}

export interface CreateCatalogoInput {
  name: string;
}

export interface AddCatalogoItemInput {
  vton_job_id?: string;
  generacion_id?: string;
  garment_name: string;
  price: number | string;
  cloth_type: "upper_body" | "lower_body" | "dress";
  sku: string;
}

export interface ReorderCatalogoItemsInput {
  ordered_item_ids: string[];
}

export interface UpdateCatalogoInput {
  name?: string;
  status?: "draft" | "published";
}

export async function getCatalogos(
  page = 1,
  pageSize = 20
): Promise<CatalogoListResponse> {
  return apiFetch(`/api/catalogos?page=${page}&page_size=${pageSize}`);
}

export async function getCatalogo(id: string): Promise<CatalogoDetail> {
  return apiFetch(`/api/catalogos/${id}`);
}

export async function createCatalogo(
  input: CreateCatalogoInput
): Promise<Catalogo> {
  return apiFetch("/api/catalogos", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function updateCatalogo(
  id: string,
  input: UpdateCatalogoInput
): Promise<Catalogo> {
  return apiFetch(`/api/catalogos/${id}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export async function deleteCatalogo(id: string): Promise<void> {
  return apiFetch(`/api/catalogos/${id}`, { method: "DELETE" });
}

export async function addCatalogoItem(
  catalogId: string,
  input: AddCatalogoItemInput
): Promise<CatalogoItem> {
  return apiFetch(`/api/catalogos/${catalogId}/items`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function removeCatalogoItem(
  catalogId: string,
  itemId: string
): Promise<void> {
  return apiFetch(`/api/catalogos/${catalogId}/items/${itemId}`, {
    method: "DELETE",
  });
}

export async function reorderCatalogoItems(
  catalogId: string,
  input: ReorderCatalogoItemsInput
): Promise<{ items: CatalogoItem[] }> {
  return apiFetch(`/api/catalogos/${catalogId}/items/reorder`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}
