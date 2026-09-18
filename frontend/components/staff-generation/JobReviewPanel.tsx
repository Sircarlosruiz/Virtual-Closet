'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Loader2,
  PlayCircle,
  RefreshCw,
  XCircle,
} from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ApiError } from '@/lib/api';
import {
  getImageGenerationJob,
  retryImageGenerationJob,
  type GenerationJobStatus,
} from '@/lib/api/image-generation';
import { listCompositionVersions } from '@/lib/api/composition';
import { getCompositionSnapshot } from '@/lib/api/templates';
import { cn } from '@/lib/utils';

const MODE_LABELS: Record<string, string> = {
  try_on: 'Prendas sobre modelo',
  text: 'Desde texto',
  edit: 'Edición',
  extraction: 'Extracción',
};

const STATUS_CONFIG: Record<
  GenerationJobStatus,
  { label: string; className: string; icon: React.ReactNode }
> = {
  queued: {
    label: 'En cola',
    className: 'text-muted-foreground',
    icon: <Clock className="size-5" />,
  },
  processing: {
    label: 'Procesando',
    className: 'text-blue-600',
    icon: <PlayCircle className="size-5 animate-pulse" />,
  },
  completed: {
    label: 'Completado — listo para revisión',
    className: 'text-green-600',
    icon: <CheckCircle2 className="size-5" />,
  },
  failed: {
    label: 'Fallido',
    className: 'text-destructive',
    icon: <XCircle className="size-5" />,
  },
};

interface JobReviewPanelProps {
  jobId: string;
}

export function JobReviewPanel({ jobId }: JobReviewPanelProps) {
  const jobQuery = useQuery({
    queryKey: ['staff-generation-job', jobId],
    queryFn: () => getImageGenerationJob(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'completed' || status === 'failed') return false;
      return 5000;
    },
  });

  const snapshotQuery = useQuery({
    queryKey: ['staff-generation-snapshot', jobId],
    queryFn: () => getCompositionSnapshot(jobId),
    enabled: Boolean(jobQuery.data),
  });

  const versionsQuery = useQuery({
    queryKey: ['staff-generation-versions', jobId],
    queryFn: () => listCompositionVersions(jobId),
    enabled: jobQuery.data?.status === 'completed',
  });

  const job = jobQuery.data;
  const latestAttempt = job?.attempts.at(-1);
  const canRetry = job?.status === 'failed';

  if (jobQuery.isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" />
        Cargando estado del trabajo…
      </div>
    );
  }

  if (jobQuery.error || !job) {
    const message = jobQuery.error instanceof Error ? jobQuery.error.message : 'Trabajo no encontrado';
    return (
      <Alert variant="destructive">
        <AlertCircle />
        <AlertTitle>No se pudo cargar el trabajo</AlertTitle>
        <AlertDescription>{message}</AlertDescription>
      </Alert>
    );
  }

  const config = STATUS_CONFIG[job.status];

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <span className={cn('shrink-0', config.className)}>{config.icon}</span>
            {config.label}
          </CardTitle>
          <CardDescription>
            Completar un trabajo lo deja listo para revisar; no publica automáticamente.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">{MODE_LABELS[job.mode] ?? job.mode}</Badge>
            <Badge variant="secondary">Proveedor {job.provider}</Badge>
          </div>
          {latestAttempt?.error_code && (
            <Alert variant="destructive">
              <AlertCircle />
              <AlertTitle>Error del proveedor o almacenamiento</AlertTitle>
              <AlertDescription>{latestAttempt.error_code}</AlertDescription>
            </Alert>
          )}
          {canRetry && (
            <RetryControl
              onRetry={async () => {
                await retryImageGenerationJob(jobId);
                await jobQuery.refetch();
              }}
            />
          )}
        </CardContent>
      </Card>

          {job.status === 'completed' && job.preview_url && (
        <Card>
          <CardHeader>
            <CardTitle>Resultado generado</CardTitle>
            <CardDescription>Imagen base sin publicar.</CardDescription>
          </CardHeader>
          <CardContent>
            {/* preview_url is a short-lived presigned URL from the API */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={job.preview_url}
              alt={`Resultado de generación ${MODE_LABELS[job.mode] ?? job.mode}`}
              className="max-h-[480px] w-full rounded-lg bg-muted object-contain"
            />
          </CardContent>
        </Card>
      )}

      {snapshotQuery.data && (
        <Card>
          <CardHeader>
            <CardTitle>Copia histórica de plantilla</CardTitle>
            <CardDescription>
              Versión {snapshotQuery.data.template_version} congelada con este trabajo.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p>Proveedor: {snapshotQuery.data.effective_configuration.provider}</p>
            {snapshotQuery.data.effective_configuration.prompt && (
              <p>Prompt: {snapshotQuery.data.effective_configuration.prompt}</p>
            )}
            {snapshotQuery.data.effective_configuration.model && (
              <p>Modelo: {snapshotQuery.data.effective_configuration.model}</p>
            )}
            {snapshotQuery.data.effective_configuration.background && (
              <p>Fondo: {snapshotQuery.data.effective_configuration.background}</p>
            )}
          </CardContent>
        </Card>
      )}

      {versionsQuery.data && versionsQuery.data.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Versiones de SKU</CardTitle>
            <CardDescription>
              El resultado original se conserva. Cada cambio de SKU o estilo crea una versión nueva.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {versionsQuery.data.map((version) => (
                <li
                  key={version.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border px-3 py-2"
                >
                  <div>
                    <p className="font-medium">
                      v{version.version} · {version.sku}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {version.placement.anchor} · {version.style.color}
                    </p>
                  </div>
                  <Badge variant={version.status === 'valid' ? 'secondary' : 'destructive'}>
                    {version.status === 'valid' ? 'válida' : 'bloqueada — no seleccionable'}
                  </Badge>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function RetryControl({ onRetry }: { onRetry: () => Promise<void> }) {
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submit() {
    setPending(true);
    setMessage(null);
    try {
      await onRetry();
      setMessage('Reintento enviado. El trabajo vuelve a la cola.');
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setMessage('Este error no se puede reintentar automáticamente.');
      } else {
        setMessage(error instanceof Error ? error.message : 'No se pudo reintentar');
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="space-y-2">
      <Button
        type="button"
        variant="outline"
        className="min-h-11"
        onClick={() => void submit()}
        disabled={pending}
      >
        {pending ? <Loader2 className="animate-spin" /> : <RefreshCw />}
        Reintentar generación
      </Button>
      {message && (
        <p className="text-sm text-muted-foreground" role="alert">
          {message}
        </p>
      )}
    </div>
  );
}
