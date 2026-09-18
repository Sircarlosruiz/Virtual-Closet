import { apiFetch } from '@/lib/api';

export interface ProductLinkLookup {
  id: string;
  system: string;
  external_product_id: string;
  external_wholesaler_id: string | null;
  is_active: boolean;
}

export async function lookupProductLink(params: {
  externalProductId: string;
  externalWholesalerId?: string;
  system?: string;
}): Promise<ProductLinkLookup> {
  const query = new URLSearchParams({
    system: params.system ?? 'bfashion',
    external_product_id: params.externalProductId,
  });
  if (params.externalWholesalerId) {
    query.set('external_wholesaler_id', params.externalWholesalerId);
  }
  return apiFetch(`/api/product-links/lookup?${query.toString()}`) as Promise<ProductLinkLookup>;
}
