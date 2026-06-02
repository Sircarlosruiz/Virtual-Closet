"use client";

import { useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { getTryoffJobs, TryoffJob } from "@/lib/api/tryoff";

function isTerminal(status: string): boolean {
  return status === "complete" || status === "failed";
}

function calcRefreshInterval(
  jobs: TryoffJob[] | undefined,
  attemptCount: number
): number | false {
  if (!jobs || jobs.length === 0) return false;
  if (jobs.every((j) => isTerminal(j.status))) return false;
  return Math.min(2000 * Math.pow(2, Math.min(attemptCount, 3)), 10000);
}

export function useTryoffJobs(jobIds: string[]) {
  const attemptRef = useRef(0);

  const { data, isLoading, isFetching, error, refetch } = useQuery({
    queryKey: ["tryoff-jobs", jobIds.sort().join(",")],
    queryFn: () => getTryoffJobs(jobIds),
    refetchInterval: (query) => {
      const jobs = query.state.data as TryoffJob[] | undefined;
      if (jobs && jobs.length > 0) {
        attemptRef.current += 1;
      }
      return calcRefreshInterval(jobs, attemptRef.current);
    },
    retry: false,
    enabled: jobIds.length > 0,
  });

  const allTerminal = data?.every((j) => isTerminal(j.status)) ?? false;

  return {
    jobs: (data ?? []) as TryoffJob[],
    isLoading: isLoading || isFetching,
    isFetching,
    error,
    refetch,
    allTerminal,
  };
}
