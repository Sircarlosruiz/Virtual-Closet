"use client";

import { TryoffJob } from "@/lib/api/tryoff";
import { JobCard } from "./job-card";
import { Skeleton } from "@/components/ui/skeleton";

interface JobListProps {
  jobs: TryoffJob[];
  isLoading: boolean;
}

export function JobList({ jobs, isLoading }: JobListProps) {
  if (isLoading && jobs.length === 0) {
    return (
      <div className="grid gap-4 sm:grid-cols-2">
        <Skeleton className="h-48 rounded-lg" />
        <Skeleton className="h-48 rounded-lg" />
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <p className="text-sm text-muted-foreground text-center py-8">
        No jobs to display.
      </p>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {jobs.map((job) => (
        <JobCard key={job.job_id} job={job} />
      ))}
    </div>
  );
}
