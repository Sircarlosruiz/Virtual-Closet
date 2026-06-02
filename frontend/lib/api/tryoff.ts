import { apiFetch } from "@/lib/api";

export type GarmentType = "upper" | "lower" | "dress";

export type TryoffJobStatus = "pending" | "queued" | "processing" | "complete" | "failed";

export interface TryoffJob {
  job_id: string;
  garment_type: GarmentType;
  status: TryoffJobStatus;
  source_image_url: string | null;
  source_image_thumb: string | null;
  output_url: string | null;
  output_media_id: string | null;
  error_reason: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface BatchSubmitInput {
  source_image_id: string;
  garment_types: GarmentType[];
}

export interface BatchSubmitResponse {
  jobs: Array<{
    job_id: string;
    status: TryoffJobStatus;
    garment_type: GarmentType;
    created_at: string;
  }>;
}

export interface SourceImageUploadResponse {
  id: string;
  presigned_url: string;
  filename: string;
  uploaded_at: string;
}

export async function uploadTryoffSourceImage(file: File): Promise<SourceImageUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch("/api/tryoff/source-images", {
    method: "POST",
    body: formData,
  });
}

export async function submitBatchJobs(
  input: BatchSubmitInput
): Promise<BatchSubmitResponse> {
  return apiFetch("/api/tryoff/jobs/batch", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function getTryoffJob(jobId: string): Promise<TryoffJob> {
  return apiFetch(`/api/tryoff/jobs/${jobId}`);
}

interface TryoffJobStatusApi {
  job_id: string;
  status: TryoffJobStatus;
  garment_type: GarmentType;
  created_at: string;
  completed_at: string | null;
  result_url: string | null;
  output_media_id: string | null;
  error_reason: string | null;
}

function mapTryoffJob(raw: TryoffJobStatusApi): TryoffJob {
  return {
    job_id: raw.job_id,
    garment_type: raw.garment_type,
    status: raw.status,
    source_image_url: null,
    source_image_thumb: null,
    output_url: raw.result_url,
    output_media_id: raw.output_media_id,
    error_reason: raw.error_reason,
    created_at: raw.created_at,
    completed_at: raw.completed_at,
  };
}

export async function getTryoffJobs(jobIds: string[]): Promise<TryoffJob[]> {
  const ids = jobIds.join(",");
  const data = (await apiFetch(
    `/api/tryoff/jobs?job_ids=${encodeURIComponent(ids)}`
  )) as TryoffJobStatusApi[];
  return data.map(mapTryoffJob);
}
