---
intent: 002-catalog-management
phase: inception
status: complete
created: 2026-05-28T00:00:00Z
updated: 2026-05-28T00:00:00Z
---

# Requirements: Catalog Management

## Intent Overview

End-to-end catalog management for the Virtual Closet B2B platform. A mayorista curates named product collections (e.g., "Summer Collection 2026") from their VTON-generated images, attaching product metadata (name, price, cloth type, SKU) to each item. The mayorista manages their catalogs (create, edit, publish, delete) and registers buyer/customer accounts. Registered customers access a buyer portal to browse the mayorista's published catalogs.

## Business Goals

| Goal | Success Metric | Priority |
|------|----------------|----------|
| Mayoristas can organize VTON outputs into product catalogs | First catalog created and published within 5 minutes of feature availability | Must |
| Customers can browse shared catalogs via a secure portal | Customer accesses buyer portal within 1 minute of receiving invitation | Must |
| Catalog items carry product context for buyer decisions | Every item includes image, name, price, cloth type, and SKU | Must |
| Only authorized customers can view a mayorista's catalogs | No unauthenticated or cross-mayorista access to any catalog | Must |

---

## Functional Requirements

### FR-1: Catalog Creation
- **Description**: Mayorista creates a named catalog to group VTON-generated images into a product collection (e.g., "Summer Collection 2026").
- **Acceptance Criteria**: `POST /api/catalogs` creates a catalog with `{name}`; catalog defaults to `draft` status; associated with the authenticated mayorista; returns `{ catalog_id, name, status, created_at }`.
- **Priority**: Must

### FR-2: Add Item to Catalog
- **Description**: Mayorista selects a completed VTON job result and adds it as a catalog item, attaching product metadata.
- **Acceptance Criteria**: `POST /api/catalogs/{catalog_id}/items` accepts `{ vton_job_id, garment_name, price, cloth_type, sku }`; validates the job belongs to the mayorista and has `status: completed`; image URL is derived from the job result; returns `{ item_id, image_url, garment_name, price, cloth_type, sku, position }`.
- **Priority**: Must

### FR-3: Remove Item from Catalog
- **Description**: Mayorista removes a garment entry from a catalog.
- **Acceptance Criteria**: `DELETE /api/catalogs/{catalog_id}/items/{item_id}` removes the item; only the catalog owner can delete; catalog remains intact; remaining items retain relative order; returns 404 if item not found.
- **Priority**: Must

### FR-4: Reorder Catalog Items
- **Description**: Mayorista changes the display order of items within a catalog.
- **Acceptance Criteria**: `PATCH /api/catalogs/{catalog_id}/items/reorder` accepts `{ ordered_item_ids: [id, id, ...] }`; validates all IDs belong to the catalog; updates positions; subsequent GET reflects new order; returns 400 if any ID is unknown or missing.
- **Priority**: Must

### FR-5: Rename Catalog
- **Description**: Mayorista updates a catalog's display name.
- **Acceptance Criteria**: `PATCH /api/catalogs/{catalog_id}` with `{ name }` updates the name; only owner can rename; returns updated catalog; 403 if not owner.
- **Priority**: Must

### FR-6: Publish / Unpublish Catalog
- **Description**: Mayorista toggles catalog visibility — published catalogs become accessible to registered customers in the buyer portal; draft catalogs are only visible to the mayorista.
- **Acceptance Criteria**: `PATCH /api/catalogs/{catalog_id}` with `{ status: "published" | "draft" }`; published catalogs appear in the buyer portal immediately; unpublishing hides them instantly; mayorista cannot publish an empty catalog (0 items).
- **Priority**: Must

### FR-7: Delete Catalog
- **Description**: Mayorista permanently deletes a catalog and all its items.
- **Acceptance Criteria**: `DELETE /api/catalogs/{catalog_id}`; only owner can delete; all items removed from DB; action is irreversible; returns 204; 403 if not owner; 404 if not found.
- **Priority**: Must

### FR-8: List Mayorista's Catalogs
- **Description**: Mayorista views a paginated list of all their catalogs with status and item count.
- **Acceptance Criteria**: `GET /api/catalogs` returns paginated list (`{ catalogs: [...], total, page }`); each entry includes `catalog_id, name, status, item_count, created_at, updated_at`; only the authenticated mayorista's catalogs are returned.
- **Priority**: Must

### FR-9: Customer Registration
- **Description**: Mayorista registers a buyer/customer so they can access the buyer portal.
- **Acceptance Criteria**: `POST /api/customers` with `{ name, email }`; customer is scoped to the authenticated mayorista; email must be unique per mayorista; customer receives an invitation email with a portal access link; returns `{ customer_id, name, email, status: "invited" }`.
- **Priority**: Must

### FR-10: Buyer Portal Authentication
- **Description**: A registered customer accesses the buyer portal via their invitation link or a magic-link login.
- **Acceptance Criteria**: Invitation link contains a signed token (JWT, 7-day TTL); customer can request a new magic-link sent to their email; valid token issues a buyer session cookie; invalid/expired token returns 401 with "Request a new link" message.
- **Priority**: Must

### FR-11: Browse Published Catalogs (Buyer Portal)
- **Description**: An authenticated customer browses the published catalogs from their mayorista.
- **Acceptance Criteria**: `GET /api/portal/catalogs` returns only published catalogs from the customer's associated mayorista; `GET /api/portal/catalogs/{catalog_id}` returns full catalog with items in mayorista-defined order; each item includes `image_url, garment_name, price, cloth_type, sku`; customer cannot access draft catalogs (404); customer cannot access another mayorista's catalogs (403).
- **Priority**: Must

---

## Non-Functional Requirements

### Performance
| Requirement | Metric | Target |
|-------------|--------|--------|
| Catalog list (mayorista) | p95 API response | < 300ms |
| Catalog detail (buyer portal) | p95 API response | < 500ms |
| Item add / reorder / delete | p95 API response | < 300ms |

### Security
| Requirement | Standard | Notes |
|-------------|----------|-------|
| Mayorista authentication | JWT HttpOnly cookie | Same as VTON pipeline |
| Customer authentication | Signed invitation token → buyer session cookie | Token expires in 7 days |
| Catalog ownership isolation | Row-level | Mayorista can only manage their own catalogs |
| Customer isolation | Row-level | Customer can only view catalogs from their mayorista |
| Image access | MinIO pre-signed URLs | Short-lived (15 min), inherited from intent 001 |

### Reliability
| Requirement | Metric | Target |
|-------------|--------|--------|
| Catalog data persistence | PostgreSQL | Same DB as VTON pipeline |
| Image delivery | MinIO pre-signed URLs | Inherited; no additional storage required |

---

## Constraints

### Technical Constraints
- Catalog items must reference a **completed** VTON job (`status: completed`) — no adding in-progress or failed job images
- Image URLs are MinIO pre-signed (short-lived), generated on-demand when a buyer loads the portal — not stored as permanent URLs
- Mayorista auth is JWT HttpOnly cookie (inherited from platform, not built here)

### Business Constraints
- A draft catalog cannot be shared — mayorista must publish before customers can view
- A catalog with 0 items cannot be published

---

## Assumptions

| Assumption | Risk if Invalid | Mitigation |
|------------|-----------------|------------|
| Mayorista authentication (JWT) already exists as platform infrastructure | Catalog endpoints have no auth guard | Enforce auth dependency at router level |
| VTON job result images are stored in MinIO and accessible | Catalog items have broken image URLs | Validate job status = completed before allowing item add |
| Email delivery infrastructure exists (SMTP/SendGrid) | Invitation emails not delivered | Abstract email sending behind a service interface; log locally in dev |

---

## Out of Scope

- PDF export of catalogs
- Batch-adding multiple VTON images at once
- Real-time notifications when mayorista publishes a catalog
- Catalog analytics (which items buyers viewed most)
- Buyer ability to "favorite" or comment on items

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Magic-link email provider (SMTP vs SendGrid)? | Carlos | TBD | Pending |
| Maximum items per catalog? | Carlos | TBD | Pending |
| Should unpublishing a catalog notify registered customers? | Carlos | TBD | Pending |
