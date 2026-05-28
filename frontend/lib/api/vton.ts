import { apiFetch } from "@/lib/api";

export interface VTONJobHistoryItem {
  job_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  cloth_type: "upper_body" | "lower_body" | "dress";
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  result_url: string | null;
  error_reason: string | null;
  retry_count: number;
}

export interface VTONJobHistoryResponse {
  items: VTONJobHistoryItem[];
  total: number;
  page: number;
  page_size: number;
}

export async function getVTONJobs(
  page = 1,
  pageSize = 50
): Promise<VTONJobHistoryResponse> {
  return apiFetch(`/api/vton/jobs?page=${page}&page_size=${pageSize}`);
}
