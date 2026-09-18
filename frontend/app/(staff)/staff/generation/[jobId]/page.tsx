'use client';

import { Suspense } from 'react';
import Link from 'next/link';
import { useParams, useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft } from 'lucide-react';

import { JobReviewPanel } from '@/components/staff-generation/JobReviewPanel';
import { ProductContextBanner } from '@/components/staff-generation/ProductContextBanner';
import { PublicationGallery } from '@/components/staff-generation/PublicationGallery';
import { SkuRecomposeForm } from '@/components/staff-generation/SkuRecomposeForm';
import { buttonVariants } from '@/components/ui/button';
import { getImageGenerationJob } from '@/lib/api/image-generation';
import { staffGenerationHref } from '@/lib/staff-generation/validate-generation-form';
import { cn } from '@/lib/utils';

function JobReviewScreen() {
  const params = useParams<{ jobId: string }>();
  const searchParams = useSearchParams();
  const jobId = params.jobId;
  const productLinkId = searchParams.get('product_link_id');
  const sku = searchParams.get('sku');
  const backHref = staffGenerationHref(null, searchParams.toString() ? `?${searchParams.toString()}` : '');

  const jobQuery = useQuery({
    queryKey: ['staff-generation-job', jobId],
    queryFn: () => getImageGenerationJob(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'completed' || status === 'failed') return false;
      return 5000;
    },
  });

  const completed = jobQuery.data?.status === 'completed';

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-6">
      <div className="flex items-center gap-3">
        <Link
          href={backHref}
          className={cn(buttonVariants({ variant: 'ghost', size: 'sm' }), 'min-h-11')}
        >
          <ArrowLeft />
          Nueva generación
        </Link>
        <h1 className="text-xl font-semibold">Revisión del trabajo</h1>
      </div>
      <ProductContextBanner />
      <JobReviewPanel jobId={jobId} />
      {completed && <SkuRecomposeForm jobId={jobId} defaultSku={sku} />}
      {completed && <PublicationGallery jobId={jobId} productLinkId={productLinkId} />}
    </div>
  );
}

export default function StaffGenerationJobPage() {
  return (
    <Suspense>
      <JobReviewScreen />
    </Suspense>
  );
}
