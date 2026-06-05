export interface BatchItemCreate {
  garment_id: string;
  model_id: string;
  cloth_type: "upper_body" | "lower_body" | "dress";
}

export interface BatchCreateRequest {
  name?: string;
  items: BatchItemCreate[];
}

export interface BatchCreateResponse {
  id: string;
  name: string;
  status: string;
  total_items: number;
  completed_count: number;
  failed_count: number;
  created_at: string;
}

export interface BatchItemResponse {
  id: string;
  garment_id: string;
  model_id: string;
  cloth_type: string;
  status: string;
  vton_job_id: string | null;
  error_message: string | null;
  retry_count: number;
  created_at: string;
}

export interface BatchDetailResponse {
  id: string;
  name: string;
  status: string;
  total_items: number;
  completed_count: number;
  failed_count: number;
  created_at: string;
  completed_at: string | null;
  items: BatchItemResponse[];
}

export interface BatchListItem {
  id: string;
  name: string;
  status: string;
  total_items: number;
  completed_count: number;
  failed_count: number;
  created_at: string;
}

export interface BatchListResponse {
  items: BatchListItem[];
  total: number;
  page: number;
  page_size: number;
}

import { apiFetch } from "@/lib/api";

export async function createBatch(
  request: BatchCreateRequest
): Promise<BatchCreateResponse> {
  return apiFetch("/api/batches", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function getBatch(batchId: string): Promise<BatchDetailResponse> {
  return apiFetch(`/api/batches/${batchId}`);
}

export async function listBatches(
  page = 1,
  pageSize = 20
): Promise<BatchListResponse> {
  return apiFetch(`/api/batches?page=${page}&page_size=${pageSize}`);
}

export async function retryBatchItem(
  batchId: string,
  itemId: string
): Promise<BatchItemResponse> {
  return apiFetch(`/api/batches/${batchId}/items/${itemId}/retry`, {
    method: "POST",
  });
}
