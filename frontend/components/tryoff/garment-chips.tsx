"use client";

import { cn } from "@/lib/utils";
import { GarmentType } from "@/lib/api/tryoff";

const GARMENT_TYPES: { value: GarmentType; label: string }[] = [
  { value: "upper", label: "Upper Garment" },
  { value: "lower", label: "Lower Garment" },
  { value: "dress", label: "Full Dress / Outfit" },
];

interface GarmentChipsProps {
  selected: Set<string>;
  onToggle: (type: GarmentType) => void;
}

export function GarmentChips({ selected, onToggle }: GarmentChipsProps) {
  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="Garment type selector">
      {GARMENT_TYPES.map(({ value, label }) => {
        const isSelected = selected.has(value);
        return (
          <button
            key={value}
            type="button"
            onClick={() => onToggle(value)}
            className={cn(
              "inline-flex items-center rounded-lg border-2 px-4 py-2 text-sm font-medium transition-all",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
              isSelected
                ? "border-primary bg-primary/10 text-primary"
                : "border-border bg-background text-muted-foreground hover:border-primary/50 hover:text-foreground"
            )}
            aria-pressed={isSelected}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
