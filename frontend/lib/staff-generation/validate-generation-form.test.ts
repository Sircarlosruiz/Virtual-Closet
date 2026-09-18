import { describe, expect, it } from 'vitest';

import {
  staffGenerationHref,
  validateGenerationForm,
  type GenerationFormValues,
} from '@/lib/staff-generation/validate-generation-form';

function base(overrides: Partial<GenerationFormValues> = {}): GenerationFormValues {
  return {
    mode: 'try_on',
    provider: 'openai',
    prompt: '',
    garmentId: null,
    modelId: null,
    clothType: null,
    referenceImageIds: [],
    ...overrides,
  };
}

describe('validateGenerationForm', () => {
  it('blocks try_on when required inputs are missing', () => {
    expect(validateGenerationForm(base())).toMatch(/prenda, modelo y tipo/i);
  });

  it('accepts try_on with garment, model, cloth type and either provider', () => {
    expect(
      validateGenerationForm(
        base({ garmentId: 'g1', modelId: 'm1', clothType: 'upper_body', provider: 'vton' }),
      ),
    ).toBeNull();
  });

  it('rejects vton for non try_on modes', () => {
    expect(validateGenerationForm(base({ mode: 'text', provider: 'vton', prompt: 'a coat' }))).toMatch(
      /solo admite el proveedor OpenAI/i,
    );
  });

  it('requires a prompt for text mode', () => {
    expect(validateGenerationForm(base({ mode: 'text', prompt: '   ' }))).toMatch(/prompt/i);
  });

  it('requires prompt and reference images for edit mode', () => {
    expect(validateGenerationForm(base({ mode: 'edit', prompt: 'make it red' }))).toMatch(/referencia/i);
    expect(
      validateGenerationForm(base({ mode: 'edit', prompt: 'make it red', referenceImageIds: ['img-1'] })),
    ).toBeNull();
  });

  it('requires a reference image for extraction', () => {
    expect(validateGenerationForm(base({ mode: 'extraction' }))).toMatch(/extracción/i);
  });
});

describe('staffGenerationHref', () => {
  it('preserves BFashion query context on the job route', () => {
    expect(
      staffGenerationHref('job-1', 'source=bfashion&external_product_id=p1'),
    ).toBe('/staff/generation/job-1?source=bfashion&external_product_id=p1');
  });
});
