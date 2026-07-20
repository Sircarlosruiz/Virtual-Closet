import { apiFetch } from "@/lib/api";

export type PoseType = "front" | "side" | "back";

export interface ModelSummary {
  id: string;
  mayorista_id: string;
  name: string;
  created_at: string;
  pose_count: number;
}

export interface ModelPose {
  id: string;
  model_id: string;
  pose: PoseType;
  presigned_url: string;
  uploaded_at: string;
}

export async function listModels(): Promise<ModelSummary[]> {
  const response = await apiFetch("/api/models");
  return response.items ?? [];
}

export async function createModel(name: string): Promise<ModelSummary> {
  return apiFetch("/api/models", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export async function listModelPoses(modelId: string): Promise<ModelPose[]> {
  const response = await apiFetch(`/api/models/${modelId}/poses`);
  return response.items ?? [];
}

export async function uploadModelPose(
  modelId: string,
  file: File,
  pose: PoseType
): Promise<ModelPose> {
  const body = new FormData();
  body.append("file", file);
  body.append("pose", pose);
  return apiFetch(`/api/models/${modelId}/poses`, {
    method: "POST",
    body,
  });
}
