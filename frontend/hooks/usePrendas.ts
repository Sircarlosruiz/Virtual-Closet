"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getPrendas, PrendaResponse } from "@/lib/api/prendas";

const PRENDAS_KEY = ["prendas"];

export function usePrendas() {
  const queryClient = useQueryClient();

  const { data, isLoading, isFetching } = useQuery({
    queryKey: PRENDAS_KEY,
    queryFn: () => getPrendas(),
  });

  const fetchNextPage = async () => {
    const nextCursor = data?.next_cursor;
    if (!nextCursor || isFetching) return;

    const nextData = await getPrendas(nextCursor);
    queryClient.setQueryData(PRENDAS_KEY, (prev: any) => ({
      items: [...(prev?.items || []), ...nextData.items],
      next_cursor: nextData.next_cursor,
    }));
  };

  return {
    prendas: (data?.items || []) as PrendaResponse[],
    isLoading: isLoading || isFetching,
    fetchNextPage,
    hasNextPage: !!data?.next_cursor,
  };
}
