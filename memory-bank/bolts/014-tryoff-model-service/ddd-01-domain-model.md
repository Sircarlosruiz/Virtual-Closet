---
unit: 001-tryoff-model-service
bolt: 014-tryoff-model-service
stage: model
status: complete
updated: 2026-05-31T12:00:00Z
---

# Static Model - TryOff Model Service

## Bounded Context

**TryOff Inference**: A self-contained bounded context responsible for garment extraction inference. This context owns the FLUX.2-klein-base-9B model pipeline and provides a single inference capability to the broader TryOff system. It has no persistence — all state is ephemeral (in-memory model weights, per-request images).

**Context Map**:
- **Upstream**: None (foundation service)
- **Downstream**: `002-tryoff-job-service` (calls POST /tryoff via HTTP)
- **Relationship**: Customer-Supplier — job service is the customer, model service is the supplier

---

## Domain Entities

- **InferenceRequest**: `source_image: SourceImage, garment_type: GarmentType` - Represents a single garment extraction request. Immutable once created. Validated at construction (image format, size, garment type). One request processed at a time.
- **InferenceResult**: `garment_image: GarmentImage, inference_time_ms: int` - Represents the output of a successful inference. Immutable. Contains the extracted garment PNG and timing metadata.

---

## Value Objects

- **GarmentType**: `value: str` - Enum-like value object. Allowed values: `upper`, `lower`, `dress`. Equality by value. Each value maps to a specific prompt template.
- **InferenceParams**: `height: int, width: int, num_inference_steps: int, guidance_scale: float` - Immutable configuration for inference execution. Defaults: height=1024, width=768, num_inference_steps=28, guidance_scale=5.0.
- **SourceImage**: `data: bytes, format: str` - Input image bytes. Constraints: format must be JPEG or PNG, size must be < 10 MB, converted to RGB before inference.
- **GarmentImage**: `data: bytes` - Output image bytes. Always PNG format. Dimensions >= 768x1024 px. White background, no human visible.
- **PromptTemplate**: `template: str` - Immutable prompt string derived from GarmentType. Contains the TRYOFF trigger word and garment-specific description.

---

## Aggregates

- **ModelPipeline** (Root): Members: `_pipeline` (Flux2KleinPipeline), `_model_ready: bool`, `_inference_lock: Lock` - Invariants: (1) Model must be fully loaded and fused before accepting inference. (2) Only one inference runs at a time (serialized by lock). (3) `_model_ready` transitions from `False → True` exactly once at startup. (4) Pipeline is never reloaded at runtime — container restart required.

---

## Domain Events

- **ModelLoaded**: Trigger: `pipeline.fuse_lora()` completes successfully at startup - Payload: `{timestamp, model_name, lora_name, vram_used_mb}`
- **InferenceStarted**: Trigger: POST /tryoff accepted and lock acquired - Payload: `{request_id, garment_type, timestamp}`
- **InferenceCompleted**: Trigger: Pipeline inference returns valid output image - Payload: `{request_id, inference_time_ms, output_dimensions}`
- **InferenceFailed**: Trigger: Pipeline raises exception during inference - Payload: `{request_id, error_type, error_message, timestamp}`

---

## Domain Services

- **InferenceService**: Operations: `run_inference(request: InferenceRequest) -> InferenceResult` - Dependencies: `ModelPipeline`, `PromptBuilder`. Orchestrates: validate request → build prompt → acquire lock → run pipeline → construct result.
- **PromptBuilder**: Operations: `build_prompt(garment_type: GarmentType) -> PromptTemplate` - Dependencies: None. Pure function mapping GarmentType to prompt string.

---

## Repository Interfaces

- **None**: This bounded context has no persistence. Model weights are loaded from filesystem (Docker volume) at startup, not through a repository pattern. Image data flows in-memory per request only.

---

## Ubiquitous Language

- **TryOff**: The garment extraction process — removing a garment from a person's photo and rendering it on a white background
- **Inference**: A single execution of the FLUX pipeline to extract a garment
- **Source Image**: The input photograph containing a person wearing garments
- **Garment Image**: The output PNG showing only the extracted garment on white background
- **LoRA**: Low-Rank Adaptation — a fine-tuning adapter fused into the base model at startup
- **Fuse**: The process of merging LoRA weights into the base model for zero per-request overhead
- **Garment Type**: Classification of the target garment (upper, lower, dress) that determines the prompt
- **Pipeline**: The loaded FLUX.2-klein model with fused LoRA, ready for inference
- **Model Ready**: State indicating the pipeline has finished loading and is accepting requests
- **VRAM**: Video RAM — GPU memory required to hold model weights (~24 GB)
