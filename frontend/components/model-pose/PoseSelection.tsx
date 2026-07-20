"use client";

import { Check } from "lucide-react";

import { cn } from "@/lib/utils";
import type { ModelPose } from "@/lib/api/model-poses";

export function PoseSelection({ poses, selectedIds, onChange }: { poses: ModelPose[]; selectedIds: string[]; onChange: (ids: string[]) => void }) {
  return <div className="grid gap-3 sm:grid-cols-3">
    {poses.map((pose) => {
      const selected = selectedIds.includes(pose.id);
      return <button key={pose.id} type="button" aria-pressed={selected} onClick={() => onChange(selected ? selectedIds.filter((id) => id !== pose.id) : [...selectedIds, pose.id])} className={cn("group relative overflow-hidden rounded-xl border-2 text-left transition", selected ? "border-primary shadow-md" : "border-border opacity-70 hover:opacity-100")}><div className="aspect-[4/5] bg-muted"><img src={pose.presigned_url} alt={`Pose ${pose.pose}`} className="h-full w-full object-cover transition group-hover:scale-[1.02]" /></div><div className="flex items-center justify-between p-3"><span className="text-sm font-medium capitalize">{pose.pose === "front" ? "Frente" : pose.pose === "side" ? "Perfil" : "Espalda"}</span><span className={cn("flex h-5 w-5 items-center justify-center rounded-full border", selected ? "border-primary bg-primary text-primary-foreground" : "border-muted-foreground/40")} aria-hidden="true">{selected && <Check className="h-3 w-3" />}</span></div></button>;
    })}
  </div>;
}
