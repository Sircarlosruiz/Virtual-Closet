import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import type { ReactNode } from 'react';

import { PublicationGallery } from '@/components/staff-generation/PublicationGallery';
import type { Publication, PublicationCandidate } from '@/lib/api/publications';

vi.mock('@/lib/api/publications', () => ({
  listPublicationCandidates: vi.fn(),
  getPublication: vi.fn(),
  createPublication: vi.fn(),
  retryPublication: vi.fn(),
}));

import {
  getPublication,
  listPublicationCandidates,
} from '@/lib/api/publications';

const listMock = vi.mocked(listPublicationCandidates);
const getMock = vi.mocked(getPublication);

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

const candidate: PublicationCandidate = {
  generation_job_id: 'job-1',
  composition_version_id: null,
  kind: 'generation_result',
  durable_object_key: 'results/job-1.png',
  preview_url: null,
  decision: 'selected',
  publication_id: 'pub-1',
  eligible: true,
};

const publication: Publication = {
  id: 'pub-1',
  product_link_id: 'link-1',
  generation_job_id: 'job-1',
  composition_version_id: null,
  decision: 'selected',
  created_at: '2026-09-18T16:00:00Z',
  updated_at: '2026-09-18T16:00:00Z',
  deliveries: [
    {
      destination: 'virtual_closet',
      status: 'synced',
      retryable: false,
      last_error: null,
      attempt_count: 1,
      external_ref: null,
      durable_object_key: 'gallery/1',
    },
    {
      destination: 'bfashion',
      status: 'failed',
      retryable: true,
      last_error: 'timeout',
      attempt_count: 1,
      external_ref: null,
      durable_object_key: 'gallery/1',
    },
  ],
};

describe('PublicationGallery', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('asks to link a product instead of fetching candidates', () => {
    render(<PublicationGallery jobId="job-1" productLinkId={null} />, { wrapper });
    expect(screen.getByText(/vincula un producto para publicar/i)).toBeInTheDocument();
    expect(listMock).not.toHaveBeenCalled();
  });

  it('shows selected, discarded and independent destination status with retry only on the failed row', async () => {
    listMock.mockResolvedValue([
      candidate,
      { ...candidate, decision: 'discarded', publication_id: null, composition_version_id: 'v2', kind: 'composition_version' },
    ]);
    getMock.mockResolvedValue(publication);

    render(<PublicationGallery jobId="job-1" productLinkId="link-1" />, { wrapper });

    expect(await screen.findByText('Seleccionado')).toBeInTheDocument();
    expect(screen.getByText('Descartado')).toBeInTheDocument();
    expect(await screen.findByText('Sincronizado')).toBeInTheDocument();
    expect(screen.getByText(/Fallido · timeout/)).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /reintentar destino/i })).toHaveLength(1);
  });
});
