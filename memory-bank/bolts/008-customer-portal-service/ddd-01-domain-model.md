---
unit: 002-customer-portal-service
bolt: 008-customer-portal-service
stage: model
status: complete
updated: 2026-05-28T17:00:00Z
---

# Static Model - 002-customer-portal-service

## Bounded Context

**Customer Portal** — manages the buyer/customer lifecycle: mayoristas register buyers, buyers authenticate via signed invitation or magic-link tokens, and authenticated buyers browse published catalogs from their associated mayorista. This context reads from the Catalog Management context (published catalogs and items) but does not modify it.

## Domain Entities

- **Customer**: `id (UUID), mayorista_id (UUID), name (string), email (string), status (CustomerStatus), invitation_token_hash (string), token_expires_at (datetime), created_at (datetime), updated_at (datetime)` — A buyer registered by a mayorista. Email is unique per mayorista (not globally). Token hash is bcrypt of the invitation/magic-link JWT — plaintext never persisted.

## Value Objects

- **CustomerStatus**: `value (enum: invited | active)` — `invited` after registration, transitions to `active` on first successful token validation.

- **CustomerEmail**: `value (string)` — Constraints: valid email format. Unique per mayorista scope.

- **InvitationToken**: `value (string, JWT)` — Payload: `{ customer_id, mayorista_id, type: "invitation" }`. TTL: 7 days. Signed with `JWT_SECRET_KEY`. Plaintext sent in email link, hash stored in DB.

- **MagicLinkToken**: `value (string, JWT)` — Payload: `{ customer_id, mayorista_id, type: "magic_link" }`. TTL: 15 minutes. Signed with `JWT_SECRET_KEY`. Short-lived for re-authentication.

- **BuyerSession**: `value (string, JWT)` — Payload: `{ customer_id, mayorista_id, type: "buyer_session" }`. TTL: 7 days. Stored in HttpOnly cookie named `buyer_session`. Separate from mayorista `access_token` cookie.

## Aggregates

- **Customer** (Aggregate Root): Members: none (single entity aggregate) - Invariants:
  1. Email must be unique per mayorista (not globally)
  2. `invitation_token_hash` is always a bcrypt hash — plaintext token never stored
  3. `token_expires_at` must be set when token hash is set
  4. Status transitions: `invited → active` (on first token validation). No reverse transition.
  5. Token type claim must match operation: "invitation" for invite flow, "magic_link" for magic-link flow
  6. Expired tokens are rejected (compare `token_expires_at` against current time)

## Domain Events

- **CustomerRegistered**: Trigger: Mayorista registers a new customer - Payload: `{ customer_id, mayorista_id, name, email, invitation_token (plaintext, for email only) }`

- **BuyerAuthenticated**: Trigger: Buyer successfully validates token - Payload: `{ customer_id, mayorista_id, session_token }`

- **MagicLinkRequested**: Trigger: Buyer requests a new magic-link - Payload: `{ customer_id, mayorista_id, email, magic_link_token (plaintext, for email only) }`

## Domain Services

- **CustomerRegistrationService**: Operations: `register_customer(mayorista_id, name, email) -> (Customer, invitation_token)` - Dependencies: `CustomerRepo`, `EmailService`, `TokenService`. Validates email uniqueness per mayorista, creates customer with `status: invited`, generates invitation JWT, stores bcrypt hash, sends invitation email asynchronously.

- **BuyerAuthService**: Operations:
  - `validate_token(token) -> BuyerSession` — Decodes JWT, verifies hash matches stored hash, checks expiry, transitions status to `active` if `invited`, returns buyer session cookie value.
  - `request_magic_link(email) -> None` — Looks up customer by email, generates magic-link JWT (15 min TTL), updates hash + expiry, sends email. Always returns 200 (no enumeration).
  - Dependencies: `CustomerRepo`, `TokenService`, `EmailService`.

- **TokenService**: Operations:
  - `create_invitation_token(customer_id, mayorista_id) -> str` — Creates JWT with 7-day TTL and `type: "invitation"`.
  - `create_magic_link_token(customer_id, mayorista_id) -> str` — Creates JWT with 15-min TTL and `type: "magic_link"`.
  - `create_buyer_session(customer_id, mayorista_id) -> str` — Creates JWT with 7-day TTL and `type: "buyer_session"`.
  - `decode_token(token) -> dict | None` — Decodes and validates JWT signature + expiry.
  - `hash_token(token) -> str` — bcrypt hash of token string.
  - `verify_token_hash(token, hash) -> bool` — bcrypt comparison.
  - Dependencies: `core.security` (bcrypt + jose JWT).

- **PortalCatalogService**: Operations:
  - `list_published_catalogs(mayorista_id, page, page_size) -> (list[Catalog], total)` — Queries published catalogs for the buyer's mayorista.
  - `get_published_catalog(catalog_id, buyer_mayorista_id) -> (Catalog, list[CatalogItem])` — Returns catalog with items if published and owned by buyer's mayorista. Returns 404 for draft, 403 for wrong mayorista.
  - Dependencies: `CatalogoRepo`, `CatalogoItemRepo`, `MinIOClient`.

## Repository Interfaces

- **CustomerRepo**: Entity: `Customer` - Methods:
  - `create(customer: Customer) -> Customer`
  - `get_by_id(customer_id: UUID) -> Customer | None`
  - `get_by_email_and_mayorista(email: str, mayorista_id: UUID) -> Customer | None`
  - `update_token_hash(customer_id: UUID, token_hash: str, expires_at: datetime) -> None`
  - `activate(customer_id: UUID) -> None`

- **CatalogoRepo** (read-only, cross-context, existing): Entity: `Catalogo` - Methods:
  - `list_published_by_mayorista(mayorista_id, page, page_size) -> (list[Catalogo], int)`
  - `get_published_by_id_and_mayorista(catalog_id, mayorista_id) -> Catalogo | None`

- **CatalogoItemRepo** (read-only, cross-context, existing): Entity: `CatalogoItem` - Methods:
  - `get_all_by_catalog(catalog_id) -> list[CatalogoItem]` (already exists)

## Ubiquitous Language

- **Customer**: A buyer registered by a mayorista to access their published catalogs
- **Buyer**: Synonym for Customer — the end user who browses the portal
- **Invitation Token**: A signed JWT (7-day TTL) sent via email to a newly registered customer
- **Magic Link**: A short-lived signed JWT (15-min TTL) sent via email for re-authentication
- **Buyer Session**: An HttpOnly cookie JWT (7-day TTL) that authenticates the buyer in the portal
- **Portal**: The buyer-facing interface at `/api/portal/*` — read-only access to published catalogs
- **Token Hash**: bcrypt hash of a token's plaintext value — stored in DB, plaintext never persisted
- **No Enumeration**: Security principle where magic-link endpoint always returns 200 regardless of whether email exists, preventing email discovery attacks
