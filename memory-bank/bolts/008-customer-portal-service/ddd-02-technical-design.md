---
unit: 002-customer-portal-service
bolt: 008-customer-portal-service
stage: design
status: complete
updated: 2026-05-28T17:30:00Z
---

# Technical Design - 002-customer-portal-service

## Architecture Overview

Extends existing FastAPI backend with customer portal domain. Follows established patterns: SQLAlchemy models, async repositories, service layer with dependency injection, Pydantic schemas, and FastAPI routers.

**Key Principles**:
- Buyer auth completely separate from mayorista auth
- Tokens hashed before storage (bcrypt)
- Email sending non-blocking (async)
- Portal endpoints read-only

## Database Schema

### Table: `customer`

```sql
CREATE TABLE customer (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mayorista_id UUID NOT NULL REFERENCES mayorista(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    email VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'invited'
        CHECK (status IN ('invited', 'active')),
    invitation_token_hash VARCHAR(255) NOT NULL,
    token_expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    UNIQUE(mayorista_id, email)
);

CREATE INDEX idx_customer_mayorista ON customer(mayorista_id);
CREATE INDEX idx_customer_email ON customer(email);
```

**Design Decisions**:
- `UNIQUE(mayorista_id, email)` — email unique per mayorista, not globally
- `invitation_token_hash` — bcrypt hash, never plaintext
- `token_expires_at` — enforces TTL (7 days for invitation, 15 min for magic-link)
- Cascade delete when mayorista deleted

## API Design

### Mayorista Endpoints (require `access_token` cookie)

#### POST /api/customers

Register a new customer and send invitation email.

**Request**:
```json
{
  "name": "Ana López",
  "email": "ana@buyer.com"
}
```

**Response** (201):
```json
{
  "id": "uuid",
  "name": "Ana López",
  "email": "ana@buyer.com",
  "status": "invited",
  "created_at": "2026-05-28T17:00:00Z"
}
```

**Errors**:
- 400: Invalid email format or empty name
- 401: Not authenticated (mayorista)
- 409: Customer with this email already exists under this mayorista

**Implementation**:
1. Validate email format (Pydantic)
2. Check uniqueness: `CustomerRepo.get_by_email_and_mayorista()`
3. Generate invitation token (7-day JWT)
4. Hash token with bcrypt
5. Create customer record
6. Send invitation email asynchronously (non-blocking)
7. Return 201

---

### Portal Endpoints (buyer-facing)

#### GET /api/portal/auth?token=<jwt>

Validate invitation or magic-link token, issue buyer session cookie.

**Query Parameters**:
- `token` (required): JWT string

**Response** (200):
```json
{
  "message": "Authentication successful",
  "customer_id": "uuid",
  "mayorista_id": "uuid"
}
```

**Side Effects**:
- Sets `buyer_session` cookie (HttpOnly, SameSite=Strict, 7-day TTL)
- Transitions customer status to `active` if `invited`

**Errors**:
- 401: Invalid token, expired token, or token not found

**Implementation**:
1. Decode JWT (verify signature + expiry)
2. Extract `customer_id` and `type` from payload
3. Fetch customer from DB
4. Verify token hash matches stored hash
5. Check `token_expires_at` not exceeded
6. Generate buyer session JWT (7-day TTL)
7. Update customer status to `active` if `invited`
8. Set `buyer_session` cookie
9. Return success

**Security**:
- Cookie: `HttpOnly=True, Secure=settings.COOKIE_SECURE, SameSite=Strict, Path=/api/portal`
- Token type validation: accepts both "invitation" and "magic_link"

---

#### POST /api/portal/magic-link

Request a new magic-link email (no authentication required).

**Request**:
```json
{
  "email": "ana@buyer.com"
}
```

**Response** (200):
```json
{
  "message": "If an account exists, a magic link has been sent"
}
```

**Implementation**:
1. Look up customer by email (no mayorista context — public endpoint)
2. If found:
   - Generate magic-link token (15-min JWT)
   - Hash token, update `invitation_token_hash` and `token_expires_at`
   - Send magic-link email asynchronously
3. Always return 200 (no enumeration)

**Security**:
- No enumeration: always return 200 regardless of email existence
- Short TTL (15 min) for magic-link tokens

---

#### GET /api/portal/catalogs

List published catalogs for authenticated buyer's mayorista.

**Query Parameters**:
- `page` (optional, default 1)
- `page_size` (optional, default 20, max 100)

**Response** (200):
```json
{
  "catalogs": [
    {
      "id": "uuid",
      "name": "Summer Collection",
      "status": "published",
      "item_count": 5,
      "created_at": "2026-05-28T10:00:00Z"
    }
  ],
  "total": 10,
  "page": 1,
  "page_size": 20
}
```

**Errors**:
- 401: No buyer session cookie

**Implementation**:
1. Extract `mayorista_id` from `buyer_session` cookie
2. Query `CatalogoRepo.list_published_by_mayorista()`
3. Return paginated list

---

#### GET /api/portal/catalogs/{catalog_id}

Get published catalog detail with items.

**Response** (200):
```json
{
  "id": "uuid",
  "name": "Summer Collection",
  "status": "published",
  "item_count": 5,
  "created_at": "2026-05-28T10:00:00Z",
  "items": [
    {
      "id": "uuid",
      "image_url": "https://minio.../presigned...",
      "garment_name": "Linen Blazer",
      "price": "89.99",
      "cloth_type": "upper_body",
      "sku": "LBZ-001",
      "position": 1
    }
  ]
}
```

**Errors**:
- 401: No buyer session cookie
- 403: Catalog belongs to different mayorista
- 404: Catalog not found or not published

**Implementation**:
1. Extract `mayorista_id` from `buyer_session` cookie
2. Fetch catalog by ID
3. If catalog not found or status != "published": return 404
4. If catalog.mayorista_id != buyer's mayorista_id: return 403
5. Fetch items ordered by position
6. Generate pre-signed URLs for each item's `image_key`
7. Return catalog with items

**Security**:
- Draft catalogs return 404 (not 403) to hide existence
- Cross-mayorista access returns 403 (explicit denial)

## File Structure

```
backend/
├── models/
│   └── customer.py                    # Customer SQLAlchemy model
├── repositories/
│   └── customer_repo.py               # CustomerRepo
├── services/
│   ├── customer_service.py            # CustomerRegistrationService, BuyerAuthService
│   ├── token_service.py               # TokenService (JWT + bcrypt)
│   └── portal_catalog_service.py      # PortalCatalogService
├── api/
│   ├── schemas/
│   │   └── customer.py                # Pydantic schemas
│   └── routers/
│       ├── customers.py               # POST /api/customers (mayorista)
│       └── portal.py                  # /api/portal/* (buyer)
├── core/
│   └── dependencies.py                # Add get_current_buyer()
└── alembic/versions/
    └── {timestamp}_create_customer_table.py
```

## Security Implementation

### Token Service (`services/token_service.py`)

```python
class TokenService:
    def create_invitation_token(self, customer_id: UUID, mayorista_id: UUID) -> str:
        """Create 7-day invitation JWT with type='invitation'."""
        payload = {
            "sub": str(customer_id),
            "mayorista_id": str(mayorista_id),
            "type": "invitation",
            "exp": datetime.now(timezone.utc) + timedelta(days=7)
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")
    
    def create_magic_link_token(self, customer_id: UUID, mayorista_id: UUID) -> str:
        """Create 15-minute magic-link JWT with type='magic_link'."""
        payload = {
            "sub": str(customer_id),
            "mayorista_id": str(mayorista_id),
            "type": "magic_link",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15)
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")
    
    def create_buyer_session(self, customer_id: UUID, mayorista_id: UUID) -> str:
        """Create 7-day buyer session JWT with type='buyer_session'."""
        payload = {
            "sub": str(customer_id),
            "mayorista_id": str(mayorista_id),
            "type": "buyer_session",
            "exp": datetime.now(timezone.utc) + timedelta(days=7)
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")
    
    def decode_token(self, token: str) -> dict | None:
        """Decode and validate JWT. Returns payload or None if invalid."""
        try:
            return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        except Exception:
            return None
    
    def hash_token(self, token: str) -> str:
        """Hash token with bcrypt."""
        return bcrypt.hashpw(token.encode(), bcrypt.gensalt()).decode()
    
    def verify_token_hash(self, token: str, hash: str) -> bool:
        """Verify token matches hash."""
        return bcrypt.checkpw(token.encode(), hash.encode())
```

### Buyer Authentication Dependency (`core/dependencies.py`)

```python
async def get_current_buyer(
    buyer_session: str | None = Cookie(None),
    db: AsyncSession = Depends(get_db),
) -> Customer:
    """Extract and validate buyer session cookie."""
    if not buyer_session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token_service = TokenService()
    payload = token_service.decode_token(buyer_session)
    
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    if payload.get("type") != "buyer_session":
        raise HTTPException(status_code=401, detail="Invalid session type")
    
    customer_id = payload.get("sub")
    if not customer_id:
        raise HTTPException(status_code=401, detail="Invalid session payload")
    
    customer_repo = CustomerRepo(db)
    customer = await customer_repo.get_by_id(UUID(customer_id))
    
    if not customer:
        raise HTTPException(status_code=401, detail="Customer not found")
    
    return customer
```

### Cookie Configuration

**Buyer Session Cookie**:
- Name: `buyer_session`
- HttpOnly: `True`
- Secure: `settings.COOKIE_SECURE` (False for dev, True for prod)
- SameSite: `Strict`
- Path: `/api/portal`
- Max-Age: 7 days (604800 seconds)

**Separation from Mayorista Auth**:
- Mayorista: `access_token` cookie, path `/api`
- Buyer: `buyer_session` cookie, path `/api/portal`
- Different JWT `type` claims prevent cross-use

## Email Integration

### Invitation Email Template

```python
async def send_invitation_email(
    customer_email: str,
    customer_name: str,
    mayorista_name: str,
    invitation_token: str
) -> None:
    """Send invitation email with signed link."""
    invitation_url = f"{settings.FRONTEND_URL}/portal/auth?token={invitation_token}"
    
    # Use existing email_service pattern (async, non-blocking)
    await send_email(
        to=customer_email,
        subject=f"{mayorista_name} te ha invitado a Virtual Closet",
        html=f"""
        <h1>¡Has sido invitado!</h1>
        <p>Hola {customer_name},</p>
        <p>{mayorista_name} te ha invitado a ver sus catálogos en Virtual Closet.</p>
        <p><a href="{invitation_url}">Haz clic aquí para acceder</a></p>
        <p>Este enlace expira en 7 días.</p>
        """
    )
```

### Magic Link Email Template

```python
async def send_magic_link_email(
    customer_email: str,
    customer_name: str,
    magic_link_token: str
) -> None:
    """Send magic-link email for re-authentication."""
    magic_link_url = f"{settings.FRONTEND_URL}/portal/auth?token={magic_link_token}"
    
    await send_email(
        to=customer_email,
        subject="Tu enlace de acceso a Virtual Closet",
        html=f"""
        <h1>Tu enlace de acceso</h1>
        <p>Hola {customer_name},</p>
        <p><a href="{magic_link_url}">Haz clic aquí para acceder</a></p>
        <p>Este enlace expira en 15 minutos.</p>
        """
    )
```

**Implementation**: Extend existing `services/email_service.py` with these functions. Use `asyncio.create_task()` for non-blocking sends.

## Cross-Context Integration

### Reading Published Catalogs

**PortalCatalogService** uses existing `CatalogoRepo` and `CatalogoItemRepo` (read-only):

```python
class PortalCatalogService:
    def __init__(
        self,
        catalogo_repo: CatalogoRepo,
        catalogo_item_repo: CatalogoItemRepo,
        minio_client: MinIOClient
    ):
        self._catalogo_repo = catalogo_repo
        self._item_repo = catalogo_item_repo
        self._minio = minio_client
    
    async def list_published_catalogs(
        self,
        mayorista_id: UUID,
        page: int,
        page_size: int
    ) -> tuple[list[Catalogo], int]:
        """List published catalogs for buyer's mayorista."""
        return await self._catalogo_repo.list_published_by_mayorista(
            mayorista_id, page, page_size
        )
    
    async def get_published_catalog(
        self,
        catalog_id: UUID,
        buyer_mayorista_id: UUID
    ) -> tuple[Catalogo, list[CatalogoItem]]:
        """Get published catalog with items if authorized."""
        catalogo = await self._catalogo_repo.get_by_id(catalog_id)
        
        if not catalogo or catalogo.status != "published":
            raise CatalogoNotFoundError("Catalog not found")
        
        if catalogo.mayorista_id != buyer_mayorista_id:
            raise CatalogoOwnershipError("Access denied")
        
        items = await self._item_repo.get_all_by_catalog(catalog_id)
        return catalogo, items
```

### Required Extensions to CatalogoRepo

Add method to existing `repositories/catalogo_repo.py`:

```python
async def list_published_by_mayorista(
    self,
    mayorista_id: UUID,
    page: int,
    page_size: int
) -> tuple[list[Catalogo], int]:
    """List published catalogs for a mayorista with pagination."""
    offset = (page - 1) * page_size
    
    count_stmt = select(func.count(Catalogo.id)).where(
        Catalogo.mayorista_id == mayorista_id,
        Catalogo.status == "published"
    )
    total_result = await self._db.execute(count_stmt)
    total = total_result.scalar() or 0
    
    list_stmt = (
        select(Catalogo)
        .where(
            Catalogo.mayorista_id == mayorista_id,
            Catalogo.status == "published"
        )
        .order_by(Catalogo.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await self._db.execute(list_stmt)
    catalogs = list(result.scalars().all())
    
    return catalogs, total
```

## Error Handling

### Domain Exceptions

```python
# services/customer_service.py
class CustomerAlreadyExistsError(Exception):
    """Customer with this email already exists under this mayorista."""

class CustomerNotFoundError(Exception):
    """Customer not found."""

class InvalidTokenError(Exception):
    """Token is invalid, expired, or hash mismatch."""
```

### HTTP Error Mapping

| Domain Exception | HTTP Status | Use Case |
|------------------|-------------|----------|
| CustomerAlreadyExistsError | 409 | Duplicate email registration |
| CustomerNotFoundError | 404 | Customer lookup fails |
| InvalidTokenError | 401 | Token validation fails |
| CatalogoNotFoundError | 404 | Catalog not found or not published |
| CatalogoOwnershipError | 403 | Cross-mayorista access attempt |

## Testing Strategy

### Unit Tests

**test_customer_service.py**:
- Register customer successfully
- Reject duplicate email (409)
- Reject invalid email format (400)
- Validate invitation token successfully
- Reject expired token (401)
- Reject invalid token hash (401)
- Request magic link (always 200)
- Transition status invited → active on first auth

**test_portal_catalog_service.py**:
- List published catalogs
- Get published catalog with items
- Reject draft catalog (404)
- Reject cross-mayorista access (403)

### Integration Tests

**test_customer_api.py**:
- POST /api/customers (mayorista auth)
- GET /api/portal/auth (token validation + cookie)
- POST /api/portal/magic-link (no auth)
- GET /api/portal/catalogs (buyer auth)
- GET /api/portal/catalogs/{id} (buyer auth)

**Security Tests**:
- Buyer session cannot access mayorista endpoints
- Mayorista session cannot access portal endpoints
- Token hash never exposed in responses
- Draft catalogs return 404 (not 403)

## Performance Considerations

### Email Sending

- **Non-blocking**: Use `asyncio.create_task()` to send emails without blocking API response
- **Failure handling**: Log errors, don't fail registration if email fails
- **Rate limiting**: Consider adding rate limit to magic-link endpoint (e.g., 3 requests/hour per email)

### Token Validation

- **Bcrypt cost**: Use default cost factor (12) — acceptable for low-frequency auth operations
- **No caching**: Token validation always hits DB (security over performance)

### Portal Queries

- **Indexing**: `idx_customer_mayorista` and `idx_customer_email` support fast lookups
- **Pagination**: Catalog list uses offset-based pagination (consistent with existing patterns)

## Migration Strategy

1. Create `customer` table with Alembic
2. Add `list_published_by_mayorista()` to existing `CatalogoRepo`
3. No changes to existing `catalogo` or `catalogo_item` tables
4. Backward compatible — no breaking changes

## Summary

This technical design implements a secure customer portal with:
- **Token-based auth**: Invitation (7-day) and magic-link (15-min) JWTs, hashed before storage
- **Separate sessions**: Buyer cookie isolated from mayorista auth
- **Read-only portal**: Buyers browse published catalogs only
- **No enumeration**: Magic-link endpoint always returns 200
- **Cross-context reads**: Portal reads catalogs without modifying them

All patterns follow existing codebase conventions (FastAPI, SQLAlchemy, async repos, Pydantic schemas).
