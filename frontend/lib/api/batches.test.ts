import { describe, it, expect, vi, beforeEach } from "vitest";
import { createBatch, getBatch, listBatches, retryBatchItem } from "./batches";
import { apiFetch } from "../api";

vi.mock("../api", () => ({
  apiFetch: vi.fn(),
}));

describe("batches API client", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("createBatch", () => {
    it("should POST to /api/batches and return response", async () => {
      const mockResponse = {
        id: "batch-1",
        name: "Test Batch",
        status: "pending",
        total_items: 2,
        completed_count: 0,
        failed_count: 0,
        created_at: "2026-06-04T00:00:00Z",
      };
      (apiFetch as jest.Mock).mockResolvedValue(mockResponse);

      const result = await createBatch({
        name: "Test Batch",
        items: [
          { garment_id: "g1", model_id: "m1", cloth_type: "upper_body" },
          { garment_id: "g2", model_id: "m2", cloth_type: "dress" },
        ],
      });

      expect(apiFetch).toHaveBeenCalledWith("/api/batches", {
        method: "POST",
        body: JSON.stringify({
          name: "Test Batch",
          items: [
            { garment_id: "g1", model_id: "m1", cloth_type: "upper_body" },
            { garment_id: "g2", model_id: "m2", cloth_type: "dress" },
          ],
        }),
      });
      expect(result).toEqual(mockResponse);
    });

    it("should omit name when undefined", async () => {
      (apiFetch as jest.Mock).mockResolvedValue({ id: "batch-1" });

      await createBatch({
        items: [
          { garment_id: "g1", model_id: "m1", cloth_type: "upper_body" },
        ],
      });

      const callArgs = (apiFetch as jest.Mock).mock.calls[0][1];
      const body = JSON.parse(callArgs.body);
      expect(body.name).toBeUndefined();
    });
  });

  describe("getBatch", () => {
    it("should GET /api/batches/{id} and return detail", async () => {
      const mockResponse = {
        id: "batch-1",
        name: "Test",
        status: "in-progress",
        total_items: 5,
        completed_count: 3,
        failed_count: 1,
        created_at: "2026-06-04T00:00:00Z",
        completed_at: null,
        items: [],
      };
      (apiFetch as jest.Mock).mockResolvedValue(mockResponse);

      const result = await getBatch("batch-1");

      expect(apiFetch).toHaveBeenCalledWith("/api/batches/batch-1");
      expect(result).toEqual(mockResponse);
    });
  });

  describe("listBatches", () => {
    it("should GET /api/batches with pagination params", async () => {
      const mockResponse = {
        items: [],
        total: 0,
        page: 2,
        page_size: 10,
      };
      (apiFetch as jest.Mock).mockResolvedValue(mockResponse);

      const result = await listBatches(2, 10);

      expect(apiFetch).toHaveBeenCalledWith("/api/batches?page=2&page_size=10");
      expect(result).toEqual(mockResponse);
    });

    it("should use default pagination when not provided", async () => {
      (apiFetch as jest.Mock).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 });

      await listBatches();

      expect(apiFetch).toHaveBeenCalledWith("/api/batches?page=1&page_size=20");
    });
  });

  describe("retryBatchItem", () => {
    it("should POST to retry endpoint and return item", async () => {
      const mockResponse = {
        id: "item-1",
        garment_id: "g1",
        model_id: "m1",
        cloth_type: "upper_body",
        status: "pending",
        vton_job_id: "job-1",
        error_message: null,
        retry_count: 1,
        created_at: "2026-06-04T00:00:00Z",
      };
      (apiFetch as jest.Mock).mockResolvedValue(mockResponse);

      const result = await retryBatchItem("batch-1", "item-1");

      expect(apiFetch).toHaveBeenCalledWith(
        "/api/batches/batch-1/items/item-1/retry",
        { method: "POST" }
      );
      expect(result).toEqual(mockResponse);
    });
  });
});
