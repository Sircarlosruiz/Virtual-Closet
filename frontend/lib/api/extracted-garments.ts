import { apiFetch } from "@/lib/api";

export type ExtractedGarment = {
  id: string;
  presigned_url: string;
  filename: string;
  garment_type: "upper" | "lower" | "dress";
  source_image_id: string;
  source_job_id: string;
  created_at: string;
};

export type ExtractedGarmentsResponse = {
  items: ExtractedGarment[];
  total: number;
  page: number;
  page_size: number;
};

export async function getExtractedGarments(
  page = 1,
  pageSize = 20
): Promise<ExtractedGarmentsResponse> {
  return apiFetch(
    `/api/media/extracted-garments?page=${page}&page_size=${pageSize}`
  );
}

export async function getExtractedGarment(
  garmentId: string
): Promise<ExtractedGarment> {
  return apiFetch(`/api/media/extracted-garments/${garmentId}`);
}
