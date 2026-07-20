import { apiFetch } from "@/lib/api";

export interface PoseSetCreateRequest {
  garment_id: string;
  model_id: string;
  cloth_type: "upper_body" | "lower_body" | "dress";
  pose_ids: string[];
}

export interface PoseSetCreateResponse {
  pose_set_id: string;
  batch_id: string;
  total_items: number;
}

export interface PoseSetItem {
  pose_type: "front" | "side" | "back" | null;
  batch_item_id: string;
  media_id: string | null;
  image_url: string | null;
  status: "pending" | "processing" | "complete" | "failed";
  error_message: string | null;
}

export interface PoseSetDetail {
  pose_set_id: string;
  batch_id: string;
  garment_id: string;
  model_id: string;
  status: string;
  items: PoseSetItem[];
}

export async function createPoseSet(
  request: PoseSetCreateRequest
): Promise<PoseSetCreateResponse> {
  return apiFetch("/api/pose-sets", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function getPoseSet(poseSetId: string): Promise<PoseSetDetail> {
  return apiFetch(`/api/pose-sets/${poseSetId}`);
}
