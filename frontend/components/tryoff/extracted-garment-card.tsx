"use client";

import { ArrowUpRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ExtractedGarment } from "@/lib/api/extracted-garments";

interface ExtractedGarmentCardProps {
  garment: ExtractedGarment;
  onOpenDetail?: (garment: ExtractedGarment) => void;
}

const GARMENT_LABELS: Record<string, string> = {
  upper: "Upper",
  lower: "Lower",
  dress: "Dress",
};

const GARMENT_VARIANT: Record<string, "default" | "secondary" | "outline"> = {
  upper: "default",
  lower: "secondary",
  dress: "outline",
};

export function ExtractedGarmentCard({
  garment,
  onOpenDetail,
}: ExtractedGarmentCardProps) {
  const router = useRouter();

  const handleUseInVton = (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    router.push(`/dashboard/generate?garment_id=${garment.id}`);
  };

  const handleClick = () => {
    onOpenDetail?.(garment);
  };

  return (
    <div
      className="group relative cursor-pointer rounded-lg border bg-card overflow-hidden transition-shadow hover:shadow-md"
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") handleClick();
      }}
    >
      <div className="relative aspect-square bg-zinc-100 dark:bg-zinc-800">
        <img
          src={garment.presigned_url}
          alt={garment.filename}
          className="w-full h-full object-cover"
        />
        <Badge
          variant={GARMENT_VARIANT[garment.garment_type] ?? "outline"}
          className="absolute top-2 left-2"
        >
          {GARMENT_LABELS[garment.garment_type] ?? garment.garment_type}
        </Badge>
        <Button
          size="sm"
          variant="secondary"
          className="absolute bottom-2 right-2 gap-1 opacity-0 group-hover:opacity-100 transition-opacity text-xs h-7"
          onClick={handleUseInVton}
        >
          Use in VTON
          <ArrowUpRight className="w-3 h-3" />
        </Button>
      </div>
      <div className="p-2">
        <p className="text-xs text-muted-foreground truncate">
          {new Date(garment.created_at).toLocaleDateString()}
        </p>
      </div>
    </div>
  );
}
