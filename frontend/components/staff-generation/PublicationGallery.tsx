'use client';

import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, Loader2, RefreshCw } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  createPublication,
  getPublication,
  listPublicationCandidates,
  retryPublication,
  type Publication,
  type PublicationCandidate,
  type SyncDelivery,
} from '@/lib/api/publications';

const DECISION_LABEL: Record<string, string> = {
  selected: 'Seleccionado',
  discarded: 'Descartado',
};

const DESTINATION_LABEL: Record<string, string> = {
  virtual_closet: 'Virtual Closet',
  bfashion: 'BFashion',
};

const SYNC_LABEL: Record<string, string> = {
  pending: 'Pendiente',
  synced: 'Sincronizado',
  failed: 'Fallido',
};

interface PublicationGalleryProps {
  jobId: string;
  productLinkId: string | null;
}

export function PublicationGallery({ jobId, productLinkId }: PublicationGalleryProps) {
  const queryClient = useQueryClient();
  const [actionError, setActionError] = useState<string | null>(null);
  const [publications, setPublications] = useState<Record<string, Publication>>({});

  const candidatesQuery = useQuery({
    queryKey: ['staff-publication-candidates', jobId, productLinkId],
    queryFn: () => listPublicationCandidates(jobId, productLinkId as string),
    enabled: Boolean(productLinkId),
  });

  useEffect(() => {
    const candidates = candidatesQuery.data ?? [];
    candidates.forEach((candidate) => {
      if (!candidate.publication_id || !productLinkId) return;
      void getPublication(candidate.publication_id, productLinkId).then((publication) => {
        setPublications((current) => ({ ...current, [publication.id]: publication }));
      });
    });
  }, [candidatesQuery.data, productLinkId]);

  if (!productLinkId) {
    return (
      <Alert>
        <AlertCircle />
        <AlertTitle>Vincula un producto para publicar</AlertTitle>
        <AlertDescription>
          Abre esta pantalla desde BFashion o añade el contexto de producto. Completar un trabajo no
          publica nada.
        </AlertDescription>
      </Alert>
    );
  }

  async function decide(candidate: PublicationCandidate, decision: 'selected' | 'discarded') {
    if (!productLinkId) return;
    setActionError(null);
    try {
      const publication = await createPublication({
        product_link_id: productLinkId,
        generation_job_id: candidate.generation_job_id,
        composition_version_id: candidate.composition_version_id,
        decision,
      });
      setPublications((current) => ({ ...current, [publication.id]: publication }));
      await queryClient.invalidateQueries({
        queryKey: ['staff-publication-candidates', jobId, productLinkId],
      });
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'No se pudo guardar la decisión');
    }
  }

  async function retry(publicationId: string) {
    if (!productLinkId) return;
    setActionError(null);
    try {
      const publication = await retryPublication(publicationId, productLinkId);
      setPublications((current) => ({ ...current, [publication.id]: publication }));
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'No se pudo reintentar la sincronización');
    }
  }

  const candidates = candidatesQuery.data ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Selección y sincronización</CardTitle>
        <CardDescription>
          Elige qué resultado añadir a la galería. Cada destino informa su estado por separado.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {candidatesQuery.isLoading && (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" />
            Cargando candidatos…
          </p>
        )}
        {actionError && (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertTitle>Error de publicación</AlertTitle>
            <AlertDescription>{actionError}</AlertDescription>
          </Alert>
        )}
        {candidates.length === 0 && !candidatesQuery.isLoading && (
          <p className="text-sm text-muted-foreground">
            No hay candidatos todavía. Espera a que el trabajo termine o crea una versión de SKU.
          </p>
        )}
        <ul className="space-y-4">
          {candidates.map((candidate) => {
            const publication = candidate.publication_id
              ? publications[candidate.publication_id]
              : undefined;
            const decision = candidate.decision ?? publication?.decision;
            const decisionLabel = decision ? DECISION_LABEL[decision] ?? decision : 'Sin decisión';
            return (
              <li
                key={`${candidate.kind}-${candidate.composition_version_id ?? 'base'}`}
                className="space-y-3 rounded-xl border p-3"
              >
                <div className="flex flex-wrap items-start gap-3">
                  {candidate.preview_url && (
                    // preview_url is a short-lived presigned URL from the API
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={candidate.preview_url}
                      alt={
                        candidate.kind === 'composition_version'
                          ? 'Candidato con SKU compuesto'
                          : 'Candidato de resultado generado'
                      }
                      className="h-24 w-24 rounded-lg bg-muted object-cover"
                    />
                  )}
                  <div className="min-w-0 flex-1 space-y-2">
                    <div className="flex flex-wrap gap-2">
                      <Badge variant="outline">
                        {candidate.kind === 'composition_version' ? 'Versión SKU' : 'Resultado original'}
                      </Badge>
                      <Badge
                        variant={
                          decision === 'selected'
                            ? 'secondary'
                            : decision === 'discarded'
                              ? 'destructive'
                              : 'outline'
                        }
                      >
                        {decisionLabel}
                      </Badge>
                      {!candidate.eligible && (
                        <Badge variant="destructive">No elegible</Badge>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        type="button"
                        className="min-h-11"
                        disabled={!candidate.eligible}
                        onClick={() => void decide(candidate, 'selected')}
                      >
                        Seleccionar
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        className="min-h-11"
                        onClick={() => void decide(candidate, 'discarded')}
                      >
                        Descartar
                      </Button>
                    </div>
                  </div>
                </div>
                {publication && (
                  <DeliveryList
                    deliveries={publication.deliveries}
                    onRetry={
                      publication.deliveries.some((item) => item.retryable && item.status === 'failed')
                        ? () => void retry(publication.id)
                        : undefined
                    }
                  />
                )}
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}

function DeliveryList({
  deliveries,
  onRetry,
}: {
  deliveries: SyncDelivery[];
  onRetry?: () => void;
}) {
  return (
    <div className="space-y-2">
      {deliveries.map((delivery) => (
        <div
          key={delivery.destination}
          className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-muted/50 px-3 py-2 text-sm"
        >
          <div>
            <p className="font-medium">
              {DESTINATION_LABEL[delivery.destination] ?? delivery.destination}
            </p>
            <p>
              {SYNC_LABEL[delivery.status] ?? delivery.status}
              {delivery.last_error ? ` · ${delivery.last_error}` : ''}
            </p>
          </div>
          {delivery.retryable && delivery.status === 'failed' && onRetry && (
            <Button type="button" variant="outline" className="min-h-11" onClick={onRetry}>
              <RefreshCw />
              Reintentar destino
            </Button>
          )}
        </div>
      ))}
    </div>
  );
}
