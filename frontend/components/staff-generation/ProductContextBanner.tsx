'use client';

import { useEffect } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { AlertCircle, Link2, Loader2 } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { lookupProductLink } from '@/lib/api/product-links';

export function ProductContextBanner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const source = searchParams.get('source');
  const externalProductId = searchParams.get('external_product_id');
  const externalWholesalerId = searchParams.get('external_wholesaler_id');
  const sku = searchParams.get('sku');
  const productLinkId = searchParams.get('product_link_id');
  const search = searchParams.toString();

  const lookupQuery = useQuery({
    queryKey: ['product-link-lookup', externalProductId, externalWholesalerId],
    queryFn: () =>
      lookupProductLink({
        externalProductId: externalProductId as string,
        externalWholesalerId: externalWholesalerId ?? undefined,
      }),
    enabled: Boolean(externalProductId),
    retry: false,
  });

  useEffect(() => {
    if (!lookupQuery.data) return;
    if (lookupQuery.data.id === productLinkId) return;
    const next = new URLSearchParams(search);
    next.set('product_link_id', lookupQuery.data.id);
    router.replace(`${pathname}?${next.toString()}`);
  }, [lookupQuery.data, pathname, productLinkId, router, search]);

  if (!source && !externalProductId && !productLinkId) {
    return null;
  }

  if (lookupQuery.isLoading) {
    return (
      <Alert>
        <Loader2 className="animate-spin" />
        <AlertTitle>Resolviendo producto</AlertTitle>
        <AlertDescription>Comprobando el vínculo explícito con BFashion…</AlertDescription>
      </Alert>
    );
  }

  if (lookupQuery.error) {
    const message =
      lookupQuery.error instanceof Error
        ? lookupQuery.error.message
        : 'No se pudo resolver el producto';
    return (
      <Alert variant="destructive">
        <AlertCircle />
        <AlertTitle>Contexto de producto no válido</AlertTitle>
        <AlertDescription>
          {message}. No se creará ningún trabajo ni se mostrarán datos de otro mayorista.
        </AlertDescription>
      </Alert>
    );
  }

  const resolvedId = lookupQuery.data?.id ?? productLinkId;

  return (
    <Alert>
      <Link2 />
      <AlertTitle>Contexto de producto</AlertTitle>
      <AlertDescription>
        <div className="mt-2 flex flex-wrap gap-2">
          {source === 'bfashion' && <Badge variant="secondary">Entrada BFashion</Badge>}
          {externalProductId && <Badge variant="outline">Producto {externalProductId}</Badge>}
          {externalWholesalerId && (
            <Badge variant="outline">Mayorista {externalWholesalerId}</Badge>
          )}
          {sku && <Badge variant="outline">SKU {sku}</Badge>}
          {resolvedId && <Badge variant="outline">Vínculo {resolvedId.slice(0, 8)}</Badge>}
        </div>
      </AlertDescription>
    </Alert>
  );
}
