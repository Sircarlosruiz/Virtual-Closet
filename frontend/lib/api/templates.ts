import { ApiError, apiFetch } from '@/lib/api';

export type TemplateScope = 'common' | 'private';
export type TemplateStatus = 'draft' | 'active' | 'archived';

export interface TemplateReference {
  id: string;
  storage_key: string;
  label: string | null;
}

export interface ImageTemplate {
  id: string;
  scope: TemplateScope;
  wholesaler_id: string | null;
  version: number;
  status: TemplateStatus;
  name: string;
  model: string | null;
  background: string | null;
  colors: Record<string, unknown> | null;
  rack: string | null;
  prompt: string | null;
  references: TemplateReference[];
  created_at: string;
  updated_at: string;
}

export interface EffectiveConfiguration {
  model: string | null;
  background: string | null;
  colors: Record<string, unknown> | null;
  rack: string | null;
  prompt: string | null;
  provider: string;
  reference_keys: string[];
  template_version: number;
}

export interface CompositionSnapshot {
  id: string;
  generation_job_id: string;
  template_id: string;
  template_version: number;
  effective_configuration: EffectiveConfiguration;
  created_at: string;
}

export async function listSelectableTemplates(
  wholesalerId: string,
): Promise<ImageTemplate[]> {
  const params = new URLSearchParams({ wholesaler_id: wholesalerId });
  return apiFetch(`/api/templates/selectable?${params.toString()}`) as Promise<ImageTemplate[]>;
}

export async function getCompositionSnapshot(
  jobId: string,
): Promise<CompositionSnapshot | null> {
  try {
    return (await apiFetch(`/api/templates/snapshots/${jobId}`)) as CompositionSnapshot;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export async function regenerateFromSnapshot(jobId: string): Promise<{ job_id: string; status: string }> {
  return apiFetch(`/api/templates/snapshots/${jobId}/regenerate`, {
    method: 'POST',
  }) as Promise<{ job_id: string; status: string }>;
}
