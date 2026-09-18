import { ShieldAlert } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

export function StaffUnauthorized() {
  return (
    <div className="mx-auto max-w-lg px-4 py-16">
      <Alert>
        <ShieldAlert />
        <AlertTitle>No autorizado</AlertTitle>
        <AlertDescription>
          Esta sección está reservada al staff. No hay controles de generación ni datos privados
          disponibles en esta cuenta.
        </AlertDescription>
      </Alert>
    </div>
  );
}
