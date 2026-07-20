"use client";

import { PoseSetResultView } from "@/components/pose-set/PoseSetResultView";

export default function PoseSetResultPage({ params }: { params: { poseSetId: string } }) {
  return <PoseSetResultView poseSetId={params.poseSetId} />;
}
