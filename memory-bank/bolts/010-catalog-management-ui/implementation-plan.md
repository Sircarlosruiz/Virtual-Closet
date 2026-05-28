---
stage: plan
bolt: 010-catalog-management-ui
created: 2026-05-28T21:30:00Z
---

## Implementation Plan: 010-catalog-management-ui

### Objective

Build the mayorista's customer management UI (register buyers, view customer list) and the buyer-facing portal (authenticate via invitation link, browse published catalogs).

### Deliverables

**1 - Customer Management Page** (`/dashboard/customers`)
- List view of registered customers with name, email, status badge (Invited/Active)
- Empty state with "Register your first customer" CTA
- "Register Customer" modal form (name + email)
- Duplicate email handling (409 → form error)
- Confirmation toast on successful registration

**2 - Buyer Portal Pages** (`/portal/*`)
- `/portal/auth?token=...` — Invitation link handler, sets buyer session cookie, redirects to portal
- `/portal` — Published catalog list for authenticated buyer
- `/portal/catalogs/{id}` — Catalog detail with item grid
- `/portal/request-link` — Expired/missing token → email form to request new magic link
- Empty state when no published catalogs
- Distinct visual style from mayorista dashboard (no mayorista nav)

**3 - Shared Components**
- `CustomerCard` / `CustomerRow` — Customer list item with status badge
- `RegisterCustomerModal` — Form for registering new customers
- `PortalLayout` — Layout for buyer portal (no mayorista nav)
- `PortalCatalogCard` — Catalog card for buyer portal
- `PortalCatalogItemCard` — Item card for buyer portal (read-only)

**4 - API Integration Layer**
- `frontend/lib/api/customers.ts` — Customer API client (add GET endpoint)
- `frontend/lib/api/portal.ts` — Portal API client
- React Query hooks for customers and portal

### Dependencies

- **008-customer-portal-service** (complete): Customer registration, buyer portal auth, published catalog APIs
- **009-catalog-management-ui** (complete): Frontend app structure, shared UI components
- **Backend gap**: `GET /api/customers` endpoint missing — needs to be added to `backend/api/routers/customers.py`

### Technical Approach

**Backend**:
- Add `GET /api/customers` endpoint to `customers.py` with pagination
- Add `CustomerListResponse` schema to `customer.py`
- Add `list_customers` method to `CustomerService` if not exists

**Frontend Routing**:
- Mayorista: `/dashboard/customers` (new page under existing dashboard layout)
- Buyer: `/portal/*` (separate route group with distinct layout, no auth redirect to mayorista login)

**Buyer Auth Flow**:
- Invitation link → `/portal/auth?token=...` → calls `GET /api/portal/auth?token=...` → sets `buyer_session` cookie → redirects to `/portal`
- Buyer session cookie scoped to `/api/portal` path (backend handles this)
- Portal pages check buyer auth via `GET /api/portal/catalogs` (401 → redirect to request-link)

**Visual Distinction**:
- Portal uses different layout, no sidebar navigation
- Simpler header with mayorista branding
- Read-only UI (no edit/delete controls)

### Acceptance Criteria

**Story 004 - Customer Management Page**:
- [ ] Customers listed with name, email, status (Invited/Active)
- [ ] Empty state with CTA when no customers
- [ ] Register form accepts name + email → new customer appears with "Invited" status
- [ ] Duplicate email shows form error "This email is already registered"
- [ ] Confirmation toast shows invitation email sent

**Story 005 - Buyer Portal Page**:
- [ ] Valid invitation link → authenticated → portal shows published catalogs
- [ ] Click catalog → detail page with item grid (image, name, price, cloth type, SKU)
- [ ] Expired token → error page with "Request a new link" option
- [ ] Request new link form → confirmation message
- [ ] No published catalogs → empty state "No collections available yet"

### File Structure

```
backend/
├── api/routers/customers.py          # Add GET / endpoint
├── api/schemas/customer.py           # Add CustomerListResponse
└── services/customer_service.py      # Add list_customers method (if needed)

frontend/
├── app/
│   ├── dashboard/
│   │   └── customers/
│   │       └── page.tsx              # Customer management page
│   └── portal/
│       ├── layout.tsx                # Portal layout (no mayorista nav)
│       ├── page.tsx                  # Catalog list for buyer
│       ├── auth/
│       │   └── page.tsx              # Invitation link handler
│       ├── request-link/
│       │   └── page.tsx              # Magic link request form
│       └── catalogs/
│           └── [id]/
│               └── page.tsx          # Catalog detail for buyer
├── components/
│   ├── customers/
│   │   ├── CustomerCard.tsx
│   │   └── RegisterCustomerModal.tsx
│   └── portal/
│       ├── PortalCatalogCard.tsx
│       └── PortalCatalogItemCard.tsx
├── hooks/
│   ├── useCustomers.ts               # React Query hooks for customers
│   └── usePortal.ts                  # React Query hooks for portal
└── lib/
    └── api/
        ├── customers.ts              # Add getCustomers function
        └── portal.ts                 # Portal API client
```
