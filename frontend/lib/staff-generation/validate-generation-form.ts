import type { GenerationMode, GenerationProvider } from '@/lib/api/image-generation';

export interface GenerationFormValues {
  mode: GenerationMode;
  provider: GenerationProvider;
  prompt: string;
  garmentId: string | null;
  modelId: string | null;
  clothType: string | null;
  referenceImageIds: string[];
}

export function validateGenerationForm(values: GenerationFormValues): string | null {
  if (values.mode !== 'try_on' && values.provider !== 'openai') {
    return 'Este modo solo admite el proveedor OpenAI';
  }

  if (values.mode === 'try_on') {
    if (!values.garmentId || !values.modelId || !values.clothType) {
      return 'Prendas sobre modelo requiere prenda, modelo y tipo de prenda';
    }
    return null;
  }

  if (values.mode === 'text' && values.prompt.trim() === '') {
    return 'La generación por texto requiere un prompt';
  }

  if (values.mode === 'edit') {
    if (values.prompt.trim() === '') {
      return 'La edición requiere instrucciones de cambio';
    }
    if (values.referenceImageIds.length === 0) {
      return 'La edición requiere al menos una imagen de referencia';
    }
  }

  if (values.mode === 'extraction' && values.referenceImageIds.length === 0) {
    return 'La extracción requiere al menos una imagen de referencia';
  }

  return null;
}

export function staffGenerationHref(jobId: string | null, search: string): string {
  const query = search.startsWith('?') || search === '' ? search : `?${search}`;
  if (jobId) {
    return `/staff/generation/${jobId}${query}`;
  }
  return `/staff/generation${query}`;
}
