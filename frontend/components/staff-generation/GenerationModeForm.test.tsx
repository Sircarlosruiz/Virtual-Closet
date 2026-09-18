import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';

import { GenerationModeForm } from '@/components/staff-generation/GenerationModeForm';

vi.mock('@/lib/api/templates', () => ({
  listSelectableTemplates: vi.fn().mockResolvedValue([]),
}));

vi.mock('@/lib/api/model-poses', () => ({
  listModels: vi.fn().mockResolvedValue([]),
  listModelPoses: vi.fn().mockResolvedValue([]),
}));

vi.mock('@/lib/api', () => ({
  apiFetch: vi.fn(),
  ApiError: class ApiError extends Error {},
}));

describe('GenerationModeForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows try_on fields by default and does not submit when they are missing', async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(
      <GenerationModeForm wholesalerId="user-1" onSubmit={onSubmit} isSubmitting={false} />,
    );

    expect(screen.getByText('Fotografía de la prenda')).toBeInTheDocument();
    expect(screen.getByText('Modelo')).toBeInTheDocument();
    expect(screen.getByText('Proveedor')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Iniciar generación' }));
    expect(await screen.findByText(/no se envió el trabajo/i)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('switches to text mode fields and keeps OpenAI as the only provider', async () => {
    const user = userEvent.setup();
    render(
      <GenerationModeForm wholesalerId="user-1" onSubmit={vi.fn()} isSubmitting={false} />,
    );

    await user.click(screen.getByRole('tab', { name: 'Desde texto' }));
    expect(await screen.findByLabelText('Prompt')).toBeInTheDocument();
    expect(screen.queryByText('Proveedor')).not.toBeInTheDocument();
    expect(screen.getByText(/este modo usa openai/i)).toBeInTheDocument();
  });
});
