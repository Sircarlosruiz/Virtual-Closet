---
intent: 006-user-authentication-accounts
phase: inception
status: units-defined
updated: 2026-06-08T00:00:00Z
---

# Units: User Authentication & Mayorista Accounts

## Decomposition Strategy

**Project type**: full-stack-web
**Backend**: Domain-driven decomposition → 2 backend service units
**Frontend**: Feature-based → 1 UI unit

## Requirement-to-Unit Mapping

| FR | Requirement | Unit |
|----|-------------|------|
| FR-1 | Mayorista registration (email+password) | 001-auth-service |
| FR-2 | Mayorista login (email+password) | 001-auth-service |
| FR-3 | Google OAuth via NextAuth | 001-auth-service |
| FR-4 | Mandatory TOTP 2FA + SMS fallback | 001-auth-service |
| FR-5 | Admin sub-role per tenant | 002-tenant-account-service |
| FR-6 | Buyer token-based catalog access | 002-tenant-account-service |
| FR-7 | Multi-tenant data isolation | 002-tenant-account-service |
| FR-8 | Password reset | 001-auth-service |
| FR-9 | JWT session management & logout | 001-auth-service |

## Units

### Unit 001: auth-service
- **Purpose**: Core authentication engine — credential management, OAuth integration, 2FA enforcement, JWT issuance, and session lifecycle
- **Responsibility**: Verifying identity and issuing tokens; does not manage tenant structure
- **Assigned Requirements**: FR-1, FR-2, FR-3, FR-4, FR-8, FR-9
- **Dependencies**: `002-tenant-account-service` (tenant lookup by email)
- **Interface**: REST API (`/auth/*` routes); issues JWT access + refresh tokens
- **Default Bolt Type**: ddd-construction-bolt
- **Estimated Stories**: ~9

### Unit 002: tenant-account-service
- **Purpose**: Multi-tenancy foundation — introduces `tenant_id` across the platform, manages the tenant model, admin sub-roles, and buyer signed-link generation
- **Responsibility**: Tenant CRUD, role assignment, cross-tenant isolation enforcement, buyer link lifecycle
- **Assigned Requirements**: FR-5, FR-6, FR-7
- **Dependencies**: None (foundational unit)
- **Interface**: REST API (`/tenants/*`, `/accounts/*`, `/buyer-links/*`); `tenant_id` middleware consumed by all other platform services
- **Default Bolt Type**: ddd-construction-bolt
- **Estimated Stories**: ~7

### Unit 003: auth-accounts-ui
- **Purpose**: Frontend for all auth and account management flows
- **Responsibility**: Login, registration, 2FA setup/challenge, password reset, admin invitation, buyer link access page, account settings
- **Assigned Requirements**: All user-facing FRs (FR-1 through FR-9)
- **Dependencies**: `001-auth-service`, `002-tenant-account-service`
- **Interface**: Next.js pages + NextAuth integration; consumes backend REST APIs
- **Default Bolt Type**: simple-construction-bolt
- **Unit Type**: frontend
- **Estimated Stories**: ~8

## Dependency Graph

```
002-tenant-account-service
        │
        ▼
001-auth-service ──► 003-auth-accounts-ui
```

`002-tenant-account-service` must be built first (introduces `tenant_id`).
`001-auth-service` depends on tenant lookup.
`003-auth-accounts-ui` depends on both backend services.

## Execution Order

1. `002-tenant-account-service` — foundational (tenant model + `tenant_id` migration)
2. `001-auth-service` — core auth (depends on tenant lookup)
3. `003-auth-accounts-ui` — frontend (depends on both services)
