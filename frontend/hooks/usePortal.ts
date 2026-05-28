"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import {
  getPortalCatalogs,
  getPortalCatalog,
  requestMagicLink,
  type PortalCatalogListResponse,
  type PortalCatalogDetail,
  type MagicLinkInput,
} from "@/lib/api/portal";
import { toast } from "sonner";

const PORTAL_CATALOGS_KEY = ["portal", "catalogs"];

export function usePortalCatalogsList(page = 1, pageSize = 20) {
  return useQuery<PortalCatalogListResponse>({
    queryKey: [...PORTAL_CATALOGS_KEY, page, pageSize],
    queryFn: () => getPortalCatalogs(page, pageSize),
    retry: false,
  });
}

export function usePortalCatalog(id: string) {
  return useQuery<PortalCatalogDetail>({
    queryKey: ["portal", "catalog", id],
    queryFn: () => getPortalCatalog(id),
    enabled: !!id,
    retry: false,
  });
}

export function useRequestMagicLink() {
  return useMutation({
    mutationFn: (input: MagicLinkInput) => requestMagicLink(input),
    onSuccess: () => {
      toast.success("Revisa tu correo para un nuevo enlace de acceso");
    },
    onError: (err: Error) => {
      toast.error(`Error: ${err.message}`);
    },
  });
}
