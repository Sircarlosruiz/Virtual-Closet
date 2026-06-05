import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { BatchItemRow } from "@/components/batch/BatchItemRow";
import type { BatchItemResponse } from "@/lib/api/batches";

describe("BatchItemRow", () => {
  const baseItem: BatchItemResponse = {
    id: "item-1",
    garment_id: "g1",
    model_id: "m1",
    cloth_type: "upper_body",
    status: "pending",
    vton_job_id: null,
    error_message: null,
    retry_count: 0,
    created_at: "2026-06-04T00:00:00Z",
  };

  it("should render pending status with gray indicator", () => {
    render(<BatchItemRow item={baseItem} />);
    expect(screen.getByText("Pendiente")).toBeTruthy();
  });

  it("should render processing status with spinner", () => {
    render(<BatchItemRow item={{ ...baseItem, status: "processing" }} />);
    expect(screen.getByText("Procesando")).toBeTruthy();
  });

  it("should render complete status with green indicator", () => {
    render(<BatchItemRow item={{ ...baseItem, status: "complete" }} />);
    expect(screen.getByText("Completado")).toBeTruthy();
  });

  it("should render failed status with red indicator and error message", () => {
    render(
      <BatchItemRow
        item={{
          ...baseItem,
          status: "failed",
          error_message: "GPU OOM: CUDA out of memory",
        }}
      />
    );
    expect(screen.getByText("Fallido")).toBeTruthy();
    expect(screen.getByText(/CUDA out of memory/)).toBeTruthy();
  });

  it("should show retry button for failed items when onRetry provided", () => {
    const onRetry = vi.fn();
    render(
      <BatchItemRow
        item={{ ...baseItem, status: "failed", error_message: "Error" }}
        onRetry={onRetry}
      />
    );
    expect(screen.getByText("Reintentar")).toBeTruthy();
  });

  it("should not show retry button for non-failed items", () => {
    render(<BatchItemRow item={{ ...baseItem, status: "complete" }} onRetry={vi.fn()} />);
    expect(screen.queryByText("Reintentar")).toBeNull();
  });

  it("should show retry count when greater than 0", () => {
    render(
      <BatchItemRow
        item={{ ...baseItem, status: "failed", retry_count: 2 }}
      />
    );
    expect(screen.getByText("Reintento #2")).toBeTruthy();
  });

  it("should render cloth type badge with formatted label", () => {
    render(<BatchItemRow item={{ ...baseItem, cloth_type: "upper_body" }} />);
    expect(screen.getByText("upper body")).toBeTruthy();
  });
});
