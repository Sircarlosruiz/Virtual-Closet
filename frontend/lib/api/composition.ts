import { ApiError, apiFetch } from '@/lib/api';

export type OverlayAnchor =
  | 'top-left'
  | 'top-center'
  | 'top-right'
  | 'center-left'
  | 'center'
  | 'center-right'
  | 'bottom-left'
  | 'bottom-center'
  | 'bottom-right';

export interface OverlayPlacement {
  anchor: OverlayAnchor;
  offset_x: number;
  offset_y: number;
  max_width?: number | null;
  max_height?: number | null;
}

export interface OverlayStyle {
  font_family: string;
  font_size: number;
  color: string;
  opacity: number;
  background_color?: string | null;
  stroke_color?: string | null;
  stroke_width: number;
}

export interface CompositionRequest {
  sku: string;
  placement?: OverlayPlacement;
  style?: OverlayStyle;
}

export interface FitResult {
  fits: boolean;
  rendered_width: number;
  rendered_height: number;
  available_width: number;
  available_height: number;
  reason: string | null;
}

export interface CompositionVersion {
  id: string;
  overlay_id: string;
  generation_job_id: string;
  version: number;
  status: string;
  sku: string;
  placement: OverlayPlacement;
  style: OverlayStyle;
  font_version: string;
  rendered_key: string | null;
  rendered_checksum: string | null;
  fit_result: FitResult;
  created_at: string;
}

export async function composeSkuOverlay(
  jobId: string,
  body: CompositionRequest,
): Promise<CompositionVersion> {
  return apiFetch(`/api/generation-jobs/${jobId}/composition`, {
    method: 'POST',
    body: JSON.stringify(body),
  }) as Promise<CompositionVersion>;
}

export async function listCompositionVersions(jobId: string): Promise<CompositionVersion[]> {
  try {
    return (await apiFetch(
      `/api/generation-jobs/${jobId}/composition/versions`,
    )) as CompositionVersion[];
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return [];
    }
    throw error;
  }
}
