---
bolt: 043-image-generation-service
created: 2026-09-17T04:07:47Z
status: proposed
---

# ADR-046: Extensible Provider Abstraction for Image Generation

## Context

Image generation supports OpenAI for text, edit, and extraction, while model
try-on must continue supporting the existing VTON provider. The new capability
must not break legacy VTON callers or expose provider-specific credentials.

## Decision

Keep the existing `VTONProvider` contract unchanged and introduce a separate
provider protocol for the image-generation service. Select the provider per
validated job and adapt the existing VTON implementation at the service
boundary.

## Rationale

This preserves compatibility while allowing OpenAI-specific capabilities to
evolve independently. Changing the legacy interface would increase regression
risk for existing try-on flows.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Modify `VTONProvider` for every mode | One interface | Breaks legacy callers and mixes unrelated capabilities | Compatibility risk |
| Use provider conditionals in the router | Quick initial implementation | Couples HTTP code to inference details | Violates layer boundaries |
| Separate image-generation protocol with adapters | Preserves contracts and supports extension | Adds a small adapter boundary | Selected |

## Consequences

### Positive

- Existing VTON integrations remain stable.
- New providers can be added without changing API routes.

### Negative

- Provider adapters require explicit capability mapping.
- Some shared input normalization is duplicated across adapters.

### Risks

- Unsupported mode/provider combinations could reach inference if validation is
  bypassed. Enforce capability validation before persistence and in the worker.

## Related

- **Stories**: 001-staff-provider-selection, 002-staff-generation-jobs
- **Standards**: `memory-bank/standards/system-architecture.md`
- **Previous ADRs**: None
