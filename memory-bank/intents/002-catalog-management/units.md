---
intent: 002-catalog-management
phase: inception
status: draft
updated: 2026-05-28T00:00:00Z
---

# Units: 002-catalog-management

## Unit Decomposition

Project type: `full-stack-web` — backend units use DDD decomposition; one frontend unit uses feature-based decomposition.

## Requirement-to-Unit Mapping

| FR | Requirement | Unit |
|----|-------------|------|
| FR-1 | Catalog creation | `001-catalog-service` |
| FR-2 | Add item to catalog | `001-catalog-service` |
| FR-3 | Remove item from catalog | `001-catalog-service` |
| FR-4 | Reorder catalog items | `001-catalog-service` |
| FR-5 | Rename catalog | `001-catalog-service` |
| FR-6 | Publish / unpublish catalog | `001-catalog-service` |
| FR-7 | Delete catalog | `001-catalog-service` |
| FR-8 | List mayorista's catalogs | `001-catalog-service` |
| FR-9 | Customer registration | `002-customer-portal-service` |
| FR-10 | Buyer portal authentication | `002-customer-portal-service` |
| FR-11 | Browse published catalogs (buyer portal) | `002-customer-portal-service` |
| All user-facing FRs | Catalog UI, customer management, buyer portal | `003-catalog-management-ui` |

## Units

### Unit 1: `001-catalog-service` (Backend)

- **Purpose**: Full lifecycle management of product catalogs and their items. Covers creation, item curation, ordering, lifecycle states (draft/published), and deletion.
- **Assigned Requirements**: FR-1, FR-2, FR-3, FR-4, FR-5, FR-6, FR-7, FR-8
- **Bolt Type**: `ddd-construction-bolt`
- **Dependencies**: VTON Pipeline (reads completed job results from shared PostgreSQL DB)
- **Depended by**: `002-customer-portal-service`, `003-catalog-management-ui`
- **Estimated Stories**: 8

### Unit 2: `002-customer-portal-service` (Backend)

- **Purpose**: Customer management (mayorista registers buyers) and buyer portal backend — authentication via invitation/magic-link and read-only catalog browsing for authenticated buyers.
- **Assigned Requirements**: FR-9, FR-10, FR-11
- **Bolt Type**: `ddd-construction-bolt`
- **Dependencies**: `001-catalog-service` (reads published catalogs for buyer portal)
- **Depended by**: `003-catalog-management-ui`
- **Estimated Stories**: 3

### Unit 3: `003-catalog-management-ui` (Frontend)

- **Purpose**: All user-facing interfaces — mayorista catalog dashboard, catalog detail/edit view, publish flow, customer management page, and the buyer portal browsing experience.
- **Assigned Requirements**: All user-facing FRs (FR-1 through FR-11 from the UI perspective)
- **Bolt Type**: `simple-construction-bolt`
- **Dependencies**: `001-catalog-service`, `002-customer-portal-service`
- **Depended by**: None
- **Estimated Stories**: 5

## Dependency Graph

```
001-catalog-service ─────────────────────────────────► 003-catalog-management-ui
        │                                                         ▲
        └──► 002-customer-portal-service ────────────────────────┘
```

Execution order:
1. `001-catalog-service` (no dependencies within intent)
2. `002-customer-portal-service` (requires 001-catalog-service)
3. `003-catalog-management-ui` (requires 001 + 002)
