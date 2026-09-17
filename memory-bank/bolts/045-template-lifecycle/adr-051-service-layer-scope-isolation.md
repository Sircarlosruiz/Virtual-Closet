---
bolt: 045-template-lifecycle
created: 2026-09-17T18:39:38Z
status: proposed
superseded_by: null
---

# ADR-051: Service-Layer-Only Scope Isolation for Template Visibility

## Context

`ImageTemplate` rows are either `common` (visible to every wholesaler) or
`private` (visible only to one assigned `wholesaler_id`). ADR-012 established
a two-layer defense-in-depth pattern for platform-wide multi-tenancy:
FastAPI dependency injection as the primary layer, plus a SQLAlchemy
`before_compile` event listener as an ORM-level safety net that auto-appends
`tenant_id` filters to every query.

Template scope isolation is narrower than platform-wide tenancy: it applies
to a single table pair (`image_templates`, `template_references`) accessed
through two purpose-built repository methods (`list_selectable`,
`get_by_id`), not to every query across the platform. Extending the global
`before_compile` listener to also understand `wholesaler_id` scoping on
`image_templates` would couple a platform-wide safety net to a
feature-specific column, and staff callers must legitimately bypass the
filter entirely for administration (create/edit/archive across all
templates).

## Decision

Enforce private/common scope isolation only at the service layer
(`TemplateLifecycleService.list_selectable` / `get_by_id`), which explicitly
receives the caller's context (staff vs. wholesaler, and `wholesaler_id` when
applicable) and applies the `scope = common OR wholesaler_id = caller_id`
filter before returning rows. No ORM-level listener is added for this table.

## Rationale

The two-layer pattern in ADR-012 exists to prevent *forgetting* to scope a
query across a platform-wide, ever-growing set of tenant-owned tables. Here,
the scoped access paths are limited to two repository methods used by a
small, known set of callers (staff administration UI, and bolt 047's
template-selection flow), making a missed-filter regression far less likely
and easy to catch with a focused test suite. Adding an ORM-level listener
would also conflict with the staff administrative path, which must see
`private` templates belonging to any wholesaler — the listener would need an
override mechanism identical to the one ADR-012 already provides for admin
operations, adding complexity without a corresponding safety gain for a
single-table concern.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Service-layer filtering only (chosen) | Simple, explicit, matches the narrow blast radius of this table | Relies on repository methods being used correctly; no ORM-level safety net | Blast radius is small (two methods, small caller set); explicit filtering is easy to test |
| Extend ADR-012's `before_compile` listener to `image_templates` | Consistent with existing tenant-isolation infrastructure | Requires an admin-override path (like ADR-012 already needs) for staff-wide visibility; couples a platform-wide listener to a feature-specific column | Added complexity not justified for a single-table, low-callsite-count concern |
| Postgres RLS on `image_templates` | Database-enforced, foolproof | Same deferral rationale as ADR-015 (RLS deferred platform-wide) | Consistent with the existing platform-wide RLS deferral decision |

## Consequences

### Positive

- No new coupling between the platform-wide tenant-isolation listener and a
  feature-specific scope column.
- Staff administrative access (which must see all templates) does not need a
  bespoke override path.
- Isolation logic is visible and testable directly in
  `TemplateLifecycleService`.

### Negative

- No ORM-level safety net for this table; a future repository method that
  forgets to apply the scope filter would not be caught automatically.
- The isolation pattern for this table diverges from the platform's
  general-purpose tenant-isolation approach, so a reader familiar with
  ADR-012 must know this exception exists.

### Risks

- **Risk**: A future engineer adds a new query path against
  `image_templates` without applying the scope filter. **Mitigation**:
  Integration tests cover cross-wholesaler private-template access
  explicitly (see `ddd-03-test-report.md` once Stage 5 runs); code review
  should treat any new `image_templates` query as scope-sensitive.

## Related

- **Stories**: 001-template-lifecycle
- **Standards**: Consider noting this exception in `coding-standards.md`
  under a future "Multi-tenancy exceptions" section if more features adopt
  the same narrow-scope pattern.
- **Previous ADRs**: ADR-012 (Multi-Layer Tenant Isolation Enforcement),
  ADR-013 (404 for Unowned Resources), ADR-015 (Postgres RLS Deferred)
