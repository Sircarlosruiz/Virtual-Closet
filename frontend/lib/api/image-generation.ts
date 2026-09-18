import { apiFetch } from '@/lib/api';

export type GenerationMode = 'try_on' | 'text' | 'edit' | 'extraction';
export type GenerationProvider = 'openai' | 'vton';
export type GenerationJobStatus = 'queued' | 'processing' | 'completed' | 'failed';

export interface ImageGenerationRequest {
  mode: GenerationMode;
  provider?: GenerationProvider;
  prompt?: string;
  garment_id?: string;
  model_id?: string;
  cloth_type?: string;
  reference_image_ids?: string[];
}

export interface ProviderAttemptSummary {
  attempt_number: number;
  status: string;
  error_code: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface UsageSummary {
  status: string;
  model: string | null;
  call_count: number | null;
}

export interface ImageGenerationResponse {
  job_id: string;
  mode: GenerationMode;
  provider: GenerationProvider;
  status: GenerationJobStatus;
  created_at: string;
}

export interface ImageGenerationDetailResponse extends ImageGenerationResponse {
  attempts: ProviderAttemptSummary[];
  usage: UsageSummary;
  preview_url: string | null;
}

export async function createImageGenerationJob(
  body: ImageGenerationRequest,
  idempotencyKey: string,
): Promise<ImageGenerationResponse> {
  return apiFetch('/api/image-generation/jobs', {
    method: 'POST',
    headers: { 'Idempotency-Key': idempotencyKey },
    body: JSON.stringify(body),
  }) as Promise<ImageGenerationResponse>;
}

export async function getImageGenerationJob(
  jobId: string,
): Promise<ImageGenerationDetailResponse> {
  return apiFetch(`/api/image-generation/jobs/${jobId}`) as Promise<ImageGenerationDetailResponse>;
}

export async function retryImageGenerationJob(
  jobId: string,
): Promise<ImageGenerationResponse> {
  return apiFetch(`/api/image-generation/jobs/${jobId}/retry`, {
    method: 'POST',
  }) as Promise<ImageGenerationResponse>;
}
