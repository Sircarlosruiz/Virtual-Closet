---
bolt: 014-tryoff-model-service
created: 2026-05-31T12:45:00Z
status: accepted
superseded_by: null
---

# ADR-003: Build-Time Weight Download for FLUX.2-klein Model

## Context

The TryOff model service requires FLUX.2-klein-base-9B (~18 GB) and virtual-tryoff-lora weights to run inference. These weights must be available before the model pipeline can initialize. The decision is whether to download weights at Docker image build time (baked into the image) or at container runtime (downloaded on first start).

The FASHN container uses a hybrid approach: weights are downloaded at runtime but cached in a Docker volume (`fashn_weights`). This works because FASHN weights are ~2 GB. FLUX weights are 9x larger.

## Decision

Download FLUX.2-klein-base-9B and virtual-tryoff-lora weights at **Docker image build time** using `huggingface-cli download`. The weights become part of the Docker image layer.

## Rationale

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Runtime download + volume cache (FASHN pattern) | Smaller image, weights updateable without rebuild | First startup takes 30+ minutes for 18 GB download; startup time unpredictable; CI/CD cannot verify model availability | Unacceptable first-start latency; cannot guarantee model is ready before healthcheck passes |
| Runtime download + pre-populated volume | Fast startup after first run | Requires manual volume seeding; not portable across environments; volume corruption requires manual intervention | Operational complexity; not self-healing |
| Build-time download (chosen) | Deterministic startup; model always available; CI validates model availability | Large image (~20 GB); image rebuild required for model updates | Trade-off acceptable: model updates are rare (LoRA is stable), and deterministic startup is critical for production reliability |

## Consequences

### Positive

- Container starts and is ready within the healthcheck `start_period` (300s) — no risk of timeout due to slow download
- CI/CD pipeline validates model availability at build time — catches HuggingFace outages before deployment
- No operational burden of managing weight volumes across environments
- Container is fully self-contained — portable across any Docker host with GPU

### Negative

- Docker image is ~20 GB (base image ~6 GB + weights ~18 GB)
- Model updates require a full image rebuild and push
- Registry storage costs increase due to large image layers

### Risks

- **HuggingFace Hub outage during build**: Build fails with descriptive error. Mitigation: CI retries with exponential backoff; cached layers avoid re-download on retry.
- **Image registry storage costs**: ~20 GB per image version. Mitigation: use registry garbage collection; limit retained versions.

## Related

- **Stories**: 001-flux-container-setup
- **Standards**: Consider adding to tech-stack.md under "AI / ML" section
- **Previous ADRs**: None
