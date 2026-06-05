"use client";

import { Suspense, useMemo } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { ArrowLeft, CheckCircle2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { JobList } from "@/components/tryoff/job-list";
import { useTryoffJobs } from "@/hooks/use-tryoff-jobs";

function TryoffStatusScreen() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const jobIdsParam = searchParams.get("job_ids") ?? "";

  const jobIds = useMemo(
    () => jobIdsParam.split(",").filter(Boolean),
    [jobIdsParam]
  );

  const { jobs, isLoading, allTerminal } = useTryoffJobs(jobIds);

  const hasFailures = allTerminal && jobs.some((j) => j.status === "failed");

  return (
    <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => router.push("/extraction/new")}
        >
          <ArrowLeft className="w-4 h-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-semibold">Extraction Status</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {jobs.length} job{jobs.length !== 1 ? "s" : ""} being processed
          </p>
        </div>
      </div>

      {allTerminal && (
        <Card
          className={
            hasFailures
              ? "border-destructive/50"
              : "border-green-500/50"
          }
        >
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              {hasFailures ? (
                <>
                  <div className="rounded-full bg-destructive/10 p-2">
                    <CheckCircle2 className="w-5 h-5 text-destructive" />
                  </div>
                  <div>
                    <p className="font-medium text-destructive">
                      Some jobs failed
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {jobs.filter((j) => j.status === "complete").length} of{" "}
                      {jobs.length} completed successfully
                    </p>
                  </div>
                </>
              ) : (
                <>
                  <div className="rounded-full bg-green-500/10 p-2">
                    <CheckCircle2 className="w-5 h-5 text-green-500" />
                  </div>
                  <div>
                    <p className="font-medium text-green-500">
                      All extractions complete
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {jobs.length} garment{jobs.length !== 1 ? "s" : ""} extracted
                      successfully
                    </p>
                  </div>
                </>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Jobs</CardTitle>
          <CardDescription>
            {isLoading && !allTerminal
              ? "Fetching job status..."
              : !allTerminal
                ? "Status updates automatically"
                : "All jobs have reached a terminal state"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <JobList jobs={jobs} isLoading={isLoading} />
        </CardContent>
      </Card>
    </div>
  );
}

export default function TryoffStatusPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-3xl mx-auto px-4 py-6 text-center text-muted-foreground">
          Loading extraction status...
        </div>
      }
    >
      <TryoffStatusScreen />
    </Suspense>
  );
}
