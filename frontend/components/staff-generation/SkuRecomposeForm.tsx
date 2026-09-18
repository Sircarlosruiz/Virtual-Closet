'use client';

import { useId, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Loader2 } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ApiError } from '@/lib/api';
import {
  composeSkuOverlay,
  type OverlayAnchor,
} from '@/lib/api/composition';

const ANCHORS: OverlayAnchor[] = [
  'top-left',
  'top-center',
  'top-right',
  'center-left',
  'center',
  'center-right',
  'bottom-left',
  'bottom-center',
  'bottom-right',
];

interface SkuRecomposeFormProps {
  jobId: string;
  defaultSku?: string | null;
}

export function SkuRecomposeForm({ jobId, defaultSku }: SkuRecomposeFormProps) {
  const skuId = useId();
  const colorId = useId();
  const anchorId = useId();
  const queryClient = useQueryClient();
  const [sku, setSku] = useState(defaultSku ?? '');
  const [color, setColor] = useState('#FFFFFF');
  const [anchor, setAnchor] = useState<OverlayAnchor>('bottom-right');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (sku.trim() === '') {
      setError('Indica el SKU exacto antes de componer.');
      return;
    }
    setPending(true);
    setError(null);
    setSuccess(null);
    try {
      const version = await composeSkuOverlay(jobId, {
        sku: sku.trim(),
        placement: { anchor, offset_x: 24, offset_y: 24 },
        style: {
          font_family: 'default',
          font_size: 48,
          color,
          opacity: 1,
          stroke_width: 0,
        },
      });
      setSuccess(`Versión ${version.version} creada. El original sigue disponible.`);
      await queryClient.invalidateQueries({ queryKey: ['staff-generation-versions', jobId] });
      await queryClient.invalidateQueries({ queryKey: ['staff-publication-candidates', jobId] });
    } catch (err) {
      if (err instanceof ApiError && err.code === 'OVERLAY_DOES_NOT_FIT') {
        setError('El SKU no cabe completo en el área configurada. Ajusta el estilo o el texto.');
      } else {
        setError(err instanceof Error ? err.message : 'No se pudo componer el SKU');
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recomponer SKU</CardTitle>
        <CardDescription>
          Cambia el código o el estilo para crear una versión nueva. Publicarla requiere una
          selección explícita.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div className="space-y-2">
            <Label htmlFor={skuId}>SKU</Label>
            <Input
              id={skuId}
              value={sku}
              onChange={(event) => setSku(event.target.value)}
              className="h-11"
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor={anchorId}>Posición</Label>
              <select
                id={anchorId}
                className="h-11 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm"
                value={anchor}
                onChange={(event) => setAnchor(event.target.value as OverlayAnchor)}
              >
                {ANCHORS.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor={colorId}>Color</Label>
              <Input
                id={colorId}
                type="color"
                value={color}
                onChange={(event) => setColor(event.target.value)}
                className="h-11"
              />
            </div>
          </div>
          {error && (
            <Alert variant="destructive">
              <AlertTitle>No se creó la versión</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          {success && (
            <p className="text-sm text-muted-foreground" role="status">
              {success}
            </p>
          )}
          <Button type="submit" className="min-h-11" disabled={pending}>
            {pending && <Loader2 className="animate-spin" />}
            Crear versión
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
