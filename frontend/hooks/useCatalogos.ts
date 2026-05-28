"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getCatalogos,
  getCatalogo,
  createCatalogo,
  updateCatalogo,
  deleteCatalogo,
  addCatalogoItem,
  removeCatalogoItem,
  reorderCatalogoItems,
  type CatalogoListResponse,
  type CatalogoDetail,
  type CreateCatalogoInput,
  type UpdateCatalogoInput,
  type AddCatalogoItemInput,
  type ReorderCatalogoItemsInput,
} from "@/lib/api/catalogos";
import { toast } from "sonner";

const CATALOGOS_KEY = ["catalogos"];

export function useCatalogosList(page = 1, pageSize = 20) {
  return useQuery<CatalogoListResponse>({
    queryKey: [...CATALOGOS_KEY, page, pageSize],
    queryFn: () => getCatalogos(page, pageSize),
  });
}

export function useCatalogo(id: string) {
  return useQuery<CatalogoDetail>({
    queryKey: ["catalogo", id],
    queryFn: () => getCatalogo(id),
    enabled: !!id,
  });
}

export function useCreateCatalogo() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: CreateCatalogoInput) => createCatalogo(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CATALOGOS_KEY });
      toast.success("Catálogo creado");
    },
    onError: (err: Error) => {
      toast.error(`Error al crear catálogo: ${err.message}`);
    },
  });
}

export function useUpdateCatalogo() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: UpdateCatalogoInput }) =>
      updateCatalogo(id, input),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: CATALOGOS_KEY });
      queryClient.invalidateQueries({
        queryKey: ["catalogo", variables.id],
      });
      toast.success("Catálogo actualizado");
    },
    onError: (err: Error) => {
      toast.error(`Error al actualizar: ${err.message}`);
    },
  });
}

export function useDeleteCatalogo() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteCatalogo(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CATALOGOS_KEY });
      toast.success("Catálogo eliminado");
    },
    onError: (err: Error) => {
      toast.error(`Error al eliminar: ${err.message}`);
    },
  });
}

export function useAddCatalogoItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      catalogId,
      input,
    }: {
      catalogId: string;
      input: AddCatalogoItemInput;
    }) => addCatalogoItem(catalogId, input),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["catalogo", variables.catalogId],
      });
      toast.success("Prenda añadida al catálogo");
    },
    onError: (err: Error) => {
      toast.error(`Error al añadir prenda: ${err.message}`);
    },
  });
}

export function useRemoveCatalogoItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      catalogId,
      itemId,
    }: {
      catalogId: string;
      itemId: string;
    }) => removeCatalogoItem(catalogId, itemId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["catalogo", variables.catalogId],
      });
      toast.success("Prenda eliminada del catálogo");
    },
    onError: (err: Error) => {
      toast.error(`Error al eliminar prenda: ${err.message}`);
    },
  });
}

export function useReorderCatalogoItems() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      catalogId,
      input,
    }: {
      catalogId: string;
      input: ReorderCatalogoItemsInput;
    }) => reorderCatalogoItems(catalogId, input),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["catalogo", variables.catalogId],
      });
    },
    onError: (err: Error) => {
      toast.error(`Error al reordenar: ${err.message}`);
    },
  });
}
