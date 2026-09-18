import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { StaffGate } from '@/components/staff-generation/StaffGate';

describe('StaffGate', () => {
  it('renders nothing for mayorista accounts', () => {
    render(
      <StaffGate role="mayorista">
        <button type="button">Iniciar generación</button>
      </StaffGate>,
    );
    expect(screen.queryByRole('button', { name: 'Iniciar generación' })).not.toBeInTheDocument();
  });

  it('renders children for staff roles', () => {
    render(
      <StaffGate role="staff">
        <button type="button">Iniciar generación</button>
      </StaffGate>,
    );
    expect(screen.getByRole('button', { name: 'Iniciar generación' })).toBeInTheDocument();
  });
});
