"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { JobStatusPoller, useJobPolling } from "@/components/vton/JobStatusPoller";
import { ResultDisplay } from "@/components/vton/ResultDisplay";

export default function JobStatusPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.id as string;

  const [lastStatus, setLastStatus] = useState<string | null>(null);
  const { data: jobData } = useJobPolling(jobId);

  const status = jobData?.status ?? lastStatus;
  const isCompleted = status === "completed";
  const isFailed = status === "failed";
  const isPending = status && !isCompleted && !isFailed;

  return (
    <div className="max-w-2xl mx-auto px-4 py-6 space-y-4">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.push("/jobs")}
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          Historial
        </Button>
        <h1 className="text-xl font-semibold">Estado del trabajo</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">
            {isCompleted && "¡Tu prueba virtual está lista!"}
            {isFailed && "Error en la generación"}
            {isPending && "Procesando tu generación"}
            {!status && "Cargando..."}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {/* Status polling - always shown */}
          <JobStatusPoller
            jobId={jobId}
            onStatusChange={setLastStatus}
          />

          {/* Result display - shown when completed or failed */}
          {(isCompleted || isFailed) && (
            <div className="mt-6 pt-6 border-t border-border">
              <ResultDisplay
                garmentUrl={null}
                resultUrl={jobData?.result_url ?? null}
                errorReason={jobData?.error_reason ?? null}
                jobId={jobId}
              />
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
