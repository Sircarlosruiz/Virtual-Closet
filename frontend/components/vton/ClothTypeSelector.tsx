"use client";

import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

type ClothType = "upper_body" | "lower_body" | "dress";

const CLOTH_TYPES: { value: ClothType; label: string }[] = [
  { value: "upper_body", label: "Parte Superior" },
  { value: "lower_body", label: "Parte Inferior" },
  { value: "dress", label: "Vestido" },
];

interface ClothTypeSelectorProps {
  onSelected: (clothType: ClothType) => void;
  selected?: ClothType | null;
}

export function ClothTypeSelector({ onSelected, selected }: ClothTypeSelectorProps) {
  return (
    <RadioGroup
      value={selected ?? undefined}
      onValueChange={(value: string) => onSelected(value as ClothType)}
      className="flex flex-wrap gap-3"
      role="radiogroup"
      aria-label="Tipo de prenda"
    >
      {CLOTH_TYPES.map(({ value, label }) => (
        <div key={value} className="flex items-center">
          <RadioGroupItem value={value} id={value} className="sr-only" />
          <Label
            htmlFor={value}
            className={cn(
              "flex items-center justify-center rounded-lg border-2 border-border px-4 py-2 cursor-pointer transition-all",
              selected === value && "border-primary bg-primary/5"
            )}
          >
            {label}
          </Label>
        </div>
      ))}
    </RadioGroup>
  );
}
