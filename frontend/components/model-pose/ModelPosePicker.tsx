"use client";

import { useEffect, useState } from "react";
import { Check, ChevronDown, Image as ImageIcon } from "lucide-react";

import { ModelSelector } from "@/components/vton/ModelSelector";
import { listModelPoses, listModels, type ModelPose, type ModelSummary } from "@/lib/api/model-poses";
import { cn } from "@/lib/utils";

export interface ModelSelection {
  modelId: string;
  modelPhotoId: string;
  poses: ModelPose[];
  named: boolean;
}

export function ModelPosePicker({ onSelected, selectedId }: { onSelected: (selection: ModelSelection) => void; selectedId?: string | null }) {
  const [models, setModels] = useState<ModelSummary[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => { listModels().then(setModels).catch(() => setModels([])); }, []);

  async function selectNamed(model: ModelSummary) {
    const poses = await listModelPoses(model.id);
    setExpanded(model.id);
    if (poses.length > 0) onSelected({ modelId: model.id, modelPhotoId: poses[0].id, poses, named: true });
  }

  return <div className="space-y-5">
    {models.length > 0 && <div className="space-y-2"><p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Mis modelos</p>{models.map((model) => <button key={model.id} type="button" onClick={() => void selectNamed(model)} className={cn("flex w-full items-center justify-between rounded-xl border p-3 text-left transition", selectedId === model.id && "border-primary bg-primary/[0.04]")}><span className="flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted"><ImageIcon className="h-4 w-4 text-muted-foreground" /></span><span><span className="block text-sm font-medium">{model.name}</span><span className="text-xs text-muted-foreground">{model.pose_count}/3 poses</span></span></span><span className="flex items-center gap-2 text-xs text-muted-foreground">{expanded === model.id && <Check className="h-4 w-4 text-primary" />}<ChevronDown className="h-4 w-4" /></span></button>)}</div>}
    <div><p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Biblioteca y fotos individuales</p><ModelSelector onSelected={(id) => onSelected({ modelId: id, modelPhotoId: id, poses: [], named: false })} selectedId={selectedId} /></div>
  </div>;
}
