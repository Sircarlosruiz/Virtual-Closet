# Implementation Plan: 035-auth-accounts-ui

## Stories

- **006-buyer-catalog-access-page**: Buyer Link Landing Page (token validation → catalog view)
- **008-account-settings-admin-buyer-links**: Account Settings — Admin List/Invite/Revoke + Buyer Link Generator

## Architecture

### Routes

| Route | Component | Description |
|-------|-----------|-------------|
| `/portal/access` | `app/portal/access/page.tsx` | Buyer link validation + catalog display |
| `/settings/account` | `app/(dashboard)/settings/account/page.tsx` | Admin management + business info |
| `/settings/buyer-links` | `app/(dashboard)/settings/buyer-links/page.tsx` | Buyer link generation + history |

### Components

| Component | Path | Purpose |
|-----------|------|---------|
| `BuyerAccessValidator` | `components/portal/buyer-access-validator.tsx` | Validates token, shows catalogs or error |
| `AdminList` | `components/settings/admin-list.tsx` | Table of admins with invite/revoke |
| `AdminInviteForm` | `components/settings/admin-invite-form.tsx` | Email input + send invitation |
| `BuyerLinkGenerator` | `components/settings/buyer-link-generator.tsx` | Catalog select + TTL + generate |
| `BuyerLinkHistory` | `components/settings/buyer-link-history.tsx` | Table of generated links with copy |

### API Integration

| Endpoint | Method | Auth | Used In |
|----------|--------|------|---------|
| `POST /api/buyer-links/validate` | POST | None | `/portal/access` |
| `GET /api/tenants/me` | GET | Auth | `/settings/account` |
| `GET /api/tenants/admins` | GET | Auth | `/settings/account` |
| `POST /api/tenants/admins/invite` | POST | Auth | `/settings/account` |
| `DELETE /api/tenants/admins/{id}` | DELETE | Auth | `/settings/account` |
| `POST /api/tenants/buyer-links` | POST | Auth | `/settings/buyer-links` |
| `GET /api/tenants/buyer-links` | GET | Auth | `/settings/buyer-links` |

### Hooks

| Hook | Purpose |
|------|---------|
| `useValidateBuyerLink` | Validates token via API |
| `useAdminList` | Fetches + manages admin list |
| `useInviteAdmin` | Mutation for inviting admin |
| `useRevokeAdmin` | Mutation for revoking admin |
| `useBuyerLinks` | Fetches + generates buyer links |

### Dependencies

- Existing `apiFetch` from `@/lib/api`
- Existing `@tanstack/react-query` for data fetching
- Existing portal layout and catalog components
- Existing dashboard layout and shell
- Existing UI components (dialog, table, button, input, etc.)

## Implementation Order

1. **Buyer access page** — `/portal/access` with token validation
2. **Settings layout** — shared settings navigation
3. **Account settings** — admin list + invite/revoke
4. **Buyer links settings** — generator + history
5. **Dashboard nav update** — link to settings pages

## Error Handling

| Error | User Message | Action |
|-------|-------------|--------|
| `link_expired` | "Este enlace ha expirado. Contactá al mayorista para uno nuevo." | Show contact info |
| `invalid_token` | "Enlace inválido. Contactá al remitente para uno nuevo." | Show request-link CTA |
| `409 Conflict (invite)` | "Ya hay una invitación pendiente para este email." | Show existing invitation |
| `403 Forbidden (revoke)` | "No podés revocar este admin." | Show error toast |
| `400 Invalid catalog scope` | "Uno o más catálogos seleccionados no existen." | Show validation error |
