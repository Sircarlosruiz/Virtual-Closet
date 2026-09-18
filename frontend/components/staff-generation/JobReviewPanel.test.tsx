import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { JobReviewPanel } from '@/components/staff-generation/JobReviewPanel';
import type { ImageGenerationDetailResponse } from '@/lib/api/image-generation';

vi.mock('@/lib/api/image-generation', () => ({
  getImageGenerationJob: vi.fn(),
  retryImageGenerationJob: vi.fn(),
}));

vi.mock('@/lib/api/templates', () => ({
  getCompositionSnapshot: vi.fn().mockResolvedValue(null),
}));

vi.mock('@/lib/api/composition', () => ({
  listCompositionVersions: vi.fn().mockResolvedValue([]),
}));

import { getImageGenerationJob } from '@/lib/api/image-generation';

const getJob = vi.mocked(getImageGenerationJob);

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

function job(
  overrides: Partial<ImageGenerationDetailResponse> = {},
): ImageGenerationDetailResponse {
  return {
    job_id: 'job-1',
    mode: 'text',
    provider: 'openai',
    status: 'failed',
    created_at: '2026-09-18T16:00:00Z',
    attempts: [
      {
        attempt_number: 1,
        status: 'failed',
        error_code: 'PROVIDER_TIMEOUT',
        started_at: '2026-09-18T16:00:00Z',
        completed_at: '2026-09-18T16:01:00Z',
      },
    ],
    usage: { status: 'unknown', model: null, call_count: null },
    preview_url: null,
    ...overrides,
  };
}

describe('JobReviewPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows provider error and retry for a failed job', async () => {
    getJob.mockResolvedValue(job());
    render(<JobReviewPanel jobId="job-1" />, { wrapper });
    expect(await screen.findByText('PROVIDER_TIMEOUT')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /reintentar generación/i })).toBeInTheDocument();
  });

  it('hides retry when the job completed', async () => {
    getJob.mockResolvedValue(job({ status: 'completed', preview_url: null, attempts: [] }));
    render(<JobReviewPanel jobId="job-1" />, { wrapper });
    expect(await screen.findByText(/listo para revisión/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /reintentar generación/i })).not.toBeInTheDocument();
  });
});
