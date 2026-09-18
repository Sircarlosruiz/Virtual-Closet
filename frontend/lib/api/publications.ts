import { apiFetch } from '@/lib/api';

export type PublicationDecision = 'selected' | 'discarded';
export type CandidateKind = 'generation_result' | 'composition_version';
export type SyncDestination = 'virtual_closet' | 'bfashion';
export type SyncStatus = 'pending' | 'synced' | 'failed';

export interface SyncDelivery {
  destination: string;
  status: string;
  retryable: boolean;
  last_error: string | null;
  attempt_count: number;
  external_ref: string | null;
  durable_object_key: string | null;
}

export interface Publication {
  id: string;
  product_link_id: string;
  generation_job_id: string;
  composition_version_id: string | null;
  decision: string;
  deliveries: SyncDelivery[];
  created_at: string;
  updated_at: string;
}

export interface PublicationCandidate {
  generation_job_id: string;
  composition_version_id: string | null;
  kind: CandidateKind;
  durable_object_key: string;
  preview_url: string | null;
  decision: string | null;
  publication_id: string | null;
  eligible: boolean;
}

export async function listPublicationCandidates(
  jobId: string,
  productLinkId: string,
): Promise<PublicationCandidate[]> {
  const params = new URLSearchParams({ product_link_id: productLinkId });
  return apiFetch(
    `/api/generation-jobs/${jobId}/publication-candidates?${params.toString()}`,
  ) as Promise<PublicationCandidate[]>;
}

export async function createPublication(body: {
  product_link_id: string;
  generation_job_id: string;
  composition_version_id?: string | null;
  decision: PublicationDecision;
}): Promise<Publication> {
  return apiFetch('/api/publications', {
    method: 'POST',
    body: JSON.stringify(body),
  }) as Promise<Publication>;
}

export async function getPublication(
  publicationId: string,
  productLinkId: string,
): Promise<Publication> {
  const params = new URLSearchParams({ product_link_id: productLinkId });
  return apiFetch(`/api/publications/${publicationId}?${params.toString()}`) as Promise<Publication>;
}

export async function retryPublication(
  publicationId: string,
  productLinkId: string,
): Promise<Publication> {
  const params = new URLSearchParams({ product_link_id: productLinkId });
  return apiFetch(`/api/publications/${publicationId}/retry?${params.toString()}`, {
    method: 'POST',
  }) as Promise<Publication>;
}
