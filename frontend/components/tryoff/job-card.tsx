"use client";

import { ArrowUpRight, Loader2, CheckCircle2, XCircle, Clock, PlayCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { TryoffJob } from "@/lib/api/tryoff";

const STATUS_CONFIG: Record<
  TryoffJob["status"],
  { label: string; variant: "default" | "secondary" | "destructive" | "outline"; icon: React.ReactNode }
> = {
  pending: {
    label: "Pending",
    variant: "outline",
    icon: <Clock className="w-3 h-3" />,
  },
  queued: {
    label: "Queued",
    variant: "secondary",
    icon: <Clock className="w-3 h-3" />,
  },
  processing: {
    label: "Processing",
    variant: "default",
    icon: <PlayCircle className="w-3 h-3 animate-pulse" />,
  },
  complete: {
    label: "Complete",
    variant: "default",
    icon: <CheckCircle2 className="w-3 h-3" />,
  },
  failed: {
    label: "Failed",
    variant: "destructive",
    icon: <XCircle className="w-3 h-3" />,
  },
};

const GARMENT_LABELS: Record<string, string> = {
  upper: "Upper Garment",
  lower: "Lower Garment",
  dress: "Full Dress",
};

interface JobCardProps {
  job: TryoffJob;
}

export function JobCard({ job }: JobCardProps) {
  const router = useRouter();
  const config = STATUS_CONFIG[job.status];

  const handleUseInVton = () => {
    if (job.output_media_id) {
      router.push(`/dashboard/generate?garment_id=${job.output_media_id}`);
    }
  };

  return (
    <Card>
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">{GARMENT_LABELS[job.garment_type] ?? job.garment_type}</span>
          <Badge variant={config.variant} className="gap-1">
            {config.icon}
            {config.label}
          </Badge>
        </div>

        {job.status === "processing" && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Extracting garment...</span>
          </div>
        )}

        {job.status === "complete" && job.output_url && (
          <div className="rounded-lg border overflow-hidden">
            <img
              src={job.output_url}
              alt={`Extracted ${GARMENT_LABELS[job.garment_type]}`}
              className="w-full h-40 object-cover"
            />
          </div>
        )}

        {job.status === "complete" && job.output_media_id && (
          <Button
            size="sm"
            variant="secondary"
            className="w-full gap-2"
            onClick={handleUseInVton}
          >
            Use in VTON
            <ArrowUpRight className="w-3 h-3" />
          </Button>
        )}

        {job.status === "complete" && !job.output_url && (
          <Skeleton className="w-full h-40 rounded-lg" />
        )}

        {job.status === "failed" && (
          <p className="text-sm text-destructive">
            {job.error_reason ?? "An unexpected error occurred. Please try again."}
          </p>
        )}

        {(job.status === "pending" || job.status === "queued") && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Clock className="w-4 h-4" />
            <span>Waiting to start...</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
