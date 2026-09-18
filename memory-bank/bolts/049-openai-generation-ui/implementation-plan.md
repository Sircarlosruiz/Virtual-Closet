---
stage: plan
bolt: 049-openai-generation-ui
created: 2026-09-18T16:38:00Z
---

## Implementation Plan: 004-openai-generation-ui

### Objective

Give platform staff a single Virtual Closet experience to submit the four generation modes, monitor jobs, preview and recompose results, then select or discard candidates and watch per-destination sync. BFashion staff reach the same flows through a deep-link that preserves product and wholesaler context. The browser never holds provider credentials; authorization and validation stay on the server.

### Scope

**In scope**
- Staff-only Next.js surfaces for form, review/recompose, and publication/sync.
- Mode-specific required/optional inputs, provider choice, and client-side validation before submit.
- Job polling, actionable provider errors, and explicit retry when the API allows it.
- SKU/style recomposition that shows the new version without hiding the original.
- Candidate gallery with `candidate` / `selected` / `discarded` and independent `virtual_closet` / `bfashion` sync status plus retry.
- BFashion entry: query-param context banner that survives form → review → publish.
- Hide generation nav and data from non-staff users (mayoristas, buyers).
- Accessible errors (text + icon, not color alone); WCAG AA.

**Out of scope**
- OpenAI/VTON calls from the browser.
- New domain rules, secret handling, or a second generation path.
- Automatic publish on job completion.
- Quality scoring.
- Implementing BFashion's React/Vite screens in `~/dev/bfashion/ecommerce` (separate repo). This bolt ships the Virtual Closet UI plus the documented deep-link/S2S contract that BFashion consumes.
- Full template CRUD admin (create/archive). V1 selects existing templates and displays snapshots when the backend has them.

### Stories in Scope

- **001-generation-form**: four modes, provider/template inputs, BFashion context, no job on invalid submit.
- **002-generation-review**: poll status, preview source/provider/snapshot/SKU, recompose versions, retry on allowed failures.
- **003-product-integration-ui**: select/discard, per-destination sync, retry without duplicate gallery items, context in both apps.

### Deliverables

1. **Staff route group** — `frontend/app/(staff)/staff/generation/`
   - `page.tsx` — generation form (four modes).
   - `[jobId]/page.tsx` — review, polling, recompose, publication gallery.
   - `layout.tsx` — staff-only gate (no generation chrome for other roles).
2. **Feature components** — `frontend/components/staff-generation/`
   - `GenerationModeForm.tsx` — mode tabs and required/optional fields.
   - `ProductContextBanner.tsx` — BFashion/product/wholesaler context.
   - `JobReviewPanel.tsx` — status, attempts, preview, snapshot, SKU versions.
   - `SkuRecomposeForm.tsx` — SKU/placement/style; keeps prior versions listed.
   - `PublicationGallery.tsx` — candidate states and per-destination sync/retry.
   - `StaffGate.tsx` — render nothing (and no private payloads) for non-staff.
3. **API clients** — `frontend/lib/api/image-generation.ts`, `templates.ts`, `composition.ts`, `publications.ts`, `product-links.ts`
4. **Auth/role** — expose `role` on `/api/auth/me` and `MayoristaProfile` so the layout can gate before fetching generation data.
5. **Product-link lookup (cookie staff)** — `GET /api/product-links/lookup` so publication can resolve an explicit link from BFashion external ids without inferring owner from SKU.
6. **Nav** — staff-only item in dashboard nav; mayorista sidebar unchanged.
7. **Deep-link contract** — documented in this plan (and a short comment in the form page): BFashion opens Virtual Closet with query params; it does not call OpenAI.
8. **Tests** — Vitest/Testing Library for form validation, gallery states, and staff gate; Playwright coverage for staff vs non-staff routes.

### Dependencies

- **047-product-generation-bridge** (complete): S2S job create/status; fail-closed `ProductLink`; BFashion never gets a provider key.
- **048-product-publication-sync** (complete): cookie + S2S select/discard/retry/candidates; per-destination `SyncDelivery`; preview URLs from durable keys.
- **046-template-composition** (complete): `POST/GET /api/generation-jobs/{id}/composition` and version list; `blocked` overlay errors.
- **045-template-lifecycle** (complete): `GET /api/templates/selectable`, snapshot read/regenerate.
- **044 / 043** (complete): `POST/GET/retry /api/image-generation/jobs`.
- **Existing UI**: Next.js App Router, shadcn/ui, React Query polling (`JobStatusPoller` pattern), `apiFetch` cookie client, sonner toasts.
- **External**: BFashion admin (`~/dev/bfashion/ecommerce`) opens the deep link and uses S2S APIs from its backend. Not implemented in this repo.

### Backend contracts the UI will call (cookie + staff role)

**Generation**
- `POST /api/image-generation/jobs` + `Idempotency-Key` → 202 `{ job_id, mode, provider, status }`
- `GET /api/image-generation/jobs/{job_id}` → status, attempts (`error_code`), usage, `preview_url`
- `POST /api/image-generation/jobs/{job_id}/retry` → 202 if failed + latest attempt `error_category=transient`; else 409

**Modes / request body (`ImageGenerationRequest`)**
- `try_on`: `garment_id`, `model_id`, `cloth_type`; provider `openai` | `vton`
- `text`: non-empty `prompt`; provider OpenAI only
- `edit`: `prompt` + `reference_image_ids`
- `extraction`: `reference_image_ids`
- Client mirrors these rules so invalid submit never fires `POST`. Server remains source of truth (422).

**Templates / snapshot**
- `GET /api/templates/selectable?wholesaler_id=`
- `GET /api/templates/snapshots/{generation_job_id}` — show frozen config when present; 404 is a valid “no snapshot” state
- `POST /api/templates/snapshots/{generation_job_id}/regenerate` — new job from history, original kept

**Composition**
- `POST /api/generation-jobs/{job_id}/composition` — new version; original result stays
- `GET /api/generation-jobs/{job_id}/composition` and `/composition/versions`
- Surface `OVERLAY_DOES_NOT_FIT` (422) and `blocked` versions as non-selectable

**Publication**
- `GET /api/generation-jobs/{job_id}/publication-candidates?product_link_id=`
- `POST /api/publications` `{ product_link_id, generation_job_id, composition_version_id?, decision }`
- `GET /api/publications/{id}?product_link_id=`
- `POST /api/publications/{id}/retry?product_link_id=`

**BFashion S2S (not called from Next.js)**
- Same workflows via `/api/integration/v1/products/...` with service headers. Next.js only uses cookies.

### Technical Approach

#### Staff gating

`MeResponse` today has no `role`, while `Mayorista.role` already exists (`admin` | `owner` | `staff` | `mayorista`). Add `role` to `/api/auth/me` and the frontend profile type. The `(staff)` layout loads session server-side: non-staff get a generic “no autorizado” page with no job/template fetches. Client `StaffGate` is defense in depth. API 403 remains the real control.

Do not add generation links to the mayorista nav (`dashboardNavItems`). Staff see one extra item: “Generación IA”.

#### Generation form

Reuse existing garment/model pickers where `try_on` needs them. Mode is a radio/tab group (`role="tablist"`). Switching mode remounts fields so stale optional values are not submitted.

Provider: visible for `try_on` (OpenAI vs VTON). Other modes lock OpenAI and show a short “solo OpenAI” note — never a silent swap.

Template (optional): load selectable templates for the wholesaler in context (BFashion `external_wholesaler_id` mapped via product link, or the staff tenant’s mayorista). Selecting a template prefills prompt/references; staff can edit before submit. `ImageGenerationRequest` has no `template_id`; V1 does not invent that field. Snapshot capture stays a backend concern; review still works without a snapshot.

Submit: generate a UUID `Idempotency-Key` per attempt, `POST` jobs, then `router.push` to `/staff/generation/{jobId}` keeping product query params.

Client validation messages (Spanish, associated labels):
- missing required fields for the mode
- empty prompt for text/edit
- VTON selected for a non-try-on mode (control disabled)

#### BFashion entry surface

Deep link (same origin, cookie session):

```text
/staff/generation?source=bfashion
  &external_product_id={id}
  &external_wholesaler_id={id}
  &sku={optional}
```

On load, `GET /api/product-links/lookup?system=bfashion&external_product_id=&external_wholesaler_id=` (staff cookie). Success: banner with product id, wholesaler id, SKU, and resolved `product_link_id` stored in the URL (`product_link_id=`) so refresh and review keep it. Failure (404/403): inline error, no job created, no other tenant data.

BFashion admin (ecommerce repo) is expected to:
1. Authenticate its staff.
2. Open this URL (or iframe) with the external ids it already has.
3. Use S2S APIs from its backend if it embeds a native UI later — never OpenAI.

This bolt does not add React/Vite screens in ecommerce.

#### Review and recompose

Poll `GET /api/image-generation/jobs/{id}` with React Query `refetchInterval` while status is `queued` or `processing` (5s, same idea as `JobStatusPoller`). Stop on `completed` / `failed`.

Show:
- status with text + icon (queued / processing / completed / failed)
- latest attempt `error_code` and retry button only when retry returns would succeed (failed job; otherwise disable with explanation)
- preview image from `preview_url` with meaningful `alt`
- provider, mode
- snapshot block if present (template name/version, frozen prompt/config)
- composition versions: original result vs each SKU version (`valid` selectable, `blocked` labeled not selectable)

Recompose: `SkuRecomposeForm` posts a new composition. On success, versions list includes the new row; the previous candidate remains. Publishing the new version requires a new explicit selection (ADR-055).

#### Publication gallery

Requires `product_link_id` (from context or a staff picker fed by lookup). Without a link, show “vincula un producto para publicar” and do not call publication APIs.

Each candidate: thumbnail, kind (`generation_result` | `composition_version`), decision badge (`sin decisión` / `seleccionado` / `descartado`). Select and discard are explicit. Completing a job never auto-selects.

After select, render each `SyncDelivery`: destination label, status (`pending` / `synced` / `failed`), `last_error`, retry only if `retryable`. Partial failure: one destination can be synced while the other is failed; retry hits only the failed row (backend already isolates). Duplicate retry keeps a single gallery item (idempotent selection id).

#### Accessibility and errors

- Labels on every control; `role="alert"` for submit/sync/provider errors.
- Status never by color alone.
- Focus-visible rings; 44px touch targets on primary actions.
- Images: descriptive `alt` (mode + SKU or “resultado de generación”).
- Spanish copy for staff UI.

#### Minimal backend additions (UI-enabling only)

1. `MeResponse.role: str` — no new auth rules.
2. `GET /api/product-links/lookup` — staff cookie, fail-closed via existing `ProductLinkService` (unknown/inactive/cross-tenant → 404/403, empty body of other tenants). Returns `{ id, system, external_product_id, external_wholesaler_id, is_active }`. No create/edit of links in this bolt.

No provider env vars in the frontend. No new Celery tasks.

### File sketch (implement stage)

```text
frontend/app/(staff)/staff/generation/layout.tsx
frontend/app/(staff)/staff/generation/page.tsx
frontend/app/(staff)/staff/generation/[jobId]/page.tsx
frontend/components/staff-generation/GenerationModeForm.tsx
frontend/components/staff-generation/ProductContextBanner.tsx
frontend/components/staff-generation/JobReviewPanel.tsx
frontend/components/staff-generation/SkuRecomposeForm.tsx
frontend/components/staff-generation/PublicationGallery.tsx
frontend/components/staff-generation/StaffGate.tsx
frontend/lib/api/image-generation.ts
frontend/lib/api/templates.ts
frontend/lib/api/composition.ts
frontend/lib/api/publications.ts
frontend/lib/api/product-links.ts
backend/api/schemas/auth.py          # role on MeResponse
backend/api/routers/product_links.py  # lookup only
```

### Testing approach (Stage 3)

- Component: mode field visibility; submit blocked when invalid; gallery badges; retry visible only if retryable; StaffGate renders empty for `mayorista`.
- Playwright: staff can open `/staff/generation`; non-staff sees no controls and no private copy; mocked 403/422/partial sync.

### Acceptance Criteria

- [ ] Staff can pick a mode and only see that mode’s required/optional inputs and allowed providers.
- [ ] Invalid or missing input explains the issue in the form and does not create a job.
- [ ] A BFashion deep link shows product and wholesaler context and keeps it through submit, review, and publish.
- [ ] Queued/processing jobs show current state on refresh; completed jobs show preview, provider, snapshot (if any), and SKU versions as distinct.
- [ ] Changing SKU/style adds a new version; the original remains listed.
- [ ] Failed jobs show a reason and an explicit retry control only when the API allows retry.
- [ ] Candidates are visually distinct as undecided, selected, or discarded; publish is never automatic.
- [ ] Partial sync shows each destination independently with retry on the failed retryable one.
- [ ] Retrying delivery does not imply a second gallery item or a new generation.
- [ ] Non-staff users have no generation nav, form, or private draft/config data.
- [ ] Provider, storage, overlay-fit, and sync errors are readable and accessible.

### Risks

- **No `template_id` on job create**: template is a UI prefill in V1; historical snapshot may be absent until backend capture is wired. Review degrades to job + preview.
- **No job list endpoint**: V1 is form → job detail, not a full history page.
- **BFashion native admin UI** lives in another repo; only the deep-link + S2S contract is delivered here.
- **Product-link lookup** is required for publication from BFashion ids; without it staff cannot call `/api/publications`.
