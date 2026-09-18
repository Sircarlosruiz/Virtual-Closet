'use client';

/**
 * BFashion admin entry: open this page with cookie staff session and
 * `/staff/generation?source=bfashion&external_product_id=...&external_wholesaler_id=...&sku=...`.
 * The browser never calls OpenAI; BFashion uses S2S APIs from its backend.
 */
import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { toast } from 'sonner';

import { GenerationModeForm } from '@/components/staff-generation/GenerationModeForm';
import { ProductContextBanner } from '@/components/staff-generation/ProductContextBanner';
import { StaffGate } from '@/components/staff-generation/StaffGate';
import { createImageGenerationJob } from '@/lib/api/image-generation';
import { fetchMe } from '@/lib/api/auth';
import { staffGenerationHref } from '@/lib/staff-generation/validate-generation-form';
import type { GenerationFormValues } from '@/lib/staff-generation/validate-generation-form';
import { useQuery } from '@tanstack/react-query';

function GenerationFormScreen() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const meQuery = useQuery({ queryKey: ['auth-me'], queryFn: fetchMe });

  const handleSubmit = async (values: GenerationFormValues) => {
    setIsSubmitting(true);
    try {
      const body = {
        mode: values.mode,
        provider: values.provider,
        prompt: values.prompt.trim() || undefined,
        garment_id: values.garmentId ?? undefined,
        model_id: values.modelId ?? undefined,
        cloth_type: values.clothType ?? undefined,
        reference_image_ids:
          values.referenceImageIds.length > 0 ? values.referenceImageIds : undefined,
      };
      const result = await createImageGenerationJob(body, crypto.randomUUID());
      toast.success('Generación iniciada');
      router.push(staffGenerationHref(result.job_id, searchParams.toString() ? `?${searchParams.toString()}` : ''));
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'No se pudo iniciar la generación');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-6">
      <div>
        <h1 className="text-2xl font-semibold">Generación de imágenes</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Elige un modo, completa solo lo necesario y envía el trabajo. La clave del proveedor nunca
          sale del servidor.
        </p>
      </div>
      <ProductContextBanner />
      <StaffGate role={meQuery.data?.role}>
        {meQuery.data && (
          <GenerationModeForm
            wholesalerId={meQuery.data.id}
            defaultSku={searchParams.get('sku')}
            onSubmit={handleSubmit}
            isSubmitting={isSubmitting}
          />
        )}
      </StaffGate>
    </div>
  );
}

export default function StaffGenerationPage() {
  return (
    <Suspense>
      <GenerationFormScreen />
    </Suspense>
  );
}
