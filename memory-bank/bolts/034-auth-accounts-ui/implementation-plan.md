# Implementation Plan: 034-auth-accounts-ui

## Stories

- **003-2fa-setup-wizard**: 2FA Method Selection + TOTP QR Setup + SMS Setup + Backup Codes Display
- **004-2fa-challenge-screen**: 2FA OTP Input (TOTP or SMS) + Backup Code Fallback

## Architecture

### Routes

| Route | Component | Description |
|-------|-----------|-------------|
| `/auth/2fa/setup` | `app/(auth)/2fa/setup/page.tsx` | Wizard: method select → configure → confirm → backup codes |
| `/auth/2fa/challenge` | `app/(auth)/2fa/challenge/page.tsx` | OTP input with TOTP/SMS toggle + backup code fallback |

### Components

| Component | Path | Purpose |
|-----------|------|---------|
| `TwoFactorSetupWizard` | `components/auth/2fa-setup-wizard.tsx` | Multi-step wizard for 2FA setup |
| `MethodSelector` | `components/auth/2fa/method-selector.tsx` | Choose TOTP or SMS |
| `TotpSetupStep` | `components/auth/2fa/totp-setup-step.tsx` | QR code + manual key + confirmation |
| `SmsSetupStep` | `components/auth/2fa/sms-setup-step.tsx` | Phone input + OTP confirmation |
| `BackupCodesStep` | `components/auth/2fa/backup-codes-step.tsx` | Display + copy + acknowledge backup codes |
| `TwoFactorChallenge` | `components/auth/2fa/two-factor-challenge.tsx` | OTP input with method toggle |
| `OtpInput` | `components/auth/2fa/otp-input.tsx` | 6-digit auto-submit input |
| `SmsResendTimer` | `components/auth/2fa/sms-resend-timer.tsx` | Countdown timer for SMS resend |

### State Management

The `challenge_token` from login must be carried between pages without exposing it in the URL.

**Approach**: Use a React context + sessionStorage (not localStorage) for the `challenge_token` and user metadata (email, 2FA method preference). sessionStorage is cleared when the tab closes, matching the security requirement that `challenge_token` expires if the user closes the tab mid-flow.

```typescript
// lib/auth/challenge-context.tsx
interface ChallengeState {
  token: string | null;
  userEmail: string | null;
  requiresSetup: boolean;
}
```

### API Integration

All 2FA endpoints require `Authorization: Bearer <challenge_token>`:

| Endpoint | Method | Used In |
|----------|--------|---------|
| `/api/auth/2fa/setup` | POST | TOTP/SMS setup initiation |
| `/api/auth/2fa/setup/confirm` | POST | Confirm setup with OTP code |
| `/api/auth/2fa/challenge` | POST | Submit TOTP or backup code |
| `/api/auth/2fa/sms/send` | POST | Resend SMS during challenge |
| `/api/auth/2fa/sms/verify` | POST | Verify SMS OTP during challenge |

### Dependencies

- `qrcode.react` — QR code rendering for TOTP setup
- Existing `apiFetch` from `@/lib/api` — HTTP client with cookie credentials
- Existing auth layout from `app/(auth)/layout.tsx` — consistent styling
- Existing UI components from `@/components/ui/` — button, input, card, etc.

## Implementation Order

1. **Challenge context** — shared state for challenge_token
2. **OTP input component** — reusable 6-digit input with auto-submit
3. **2FA challenge page** — simpler page, unblocks the login flow
4. **2FA setup wizard** — multi-step flow with method selection
5. **Middleware update** — handle partial auth state (challenge_token present but no access_token)
6. **Login page integration** — store challenge_token on login response

## Middleware Changes

The current `proxy.ts` needs to recognize a new intermediate state:

- **partial-auth**: has `challenge_token` cookie but no `access_token` → allow `/auth/2fa/*` routes
- Add `/auth/2fa` to public routes matcher

## Error Handling

| Error | User Message | Action |
|-------|-------------|--------|
| `INVALID_CHALLENGE_TOKEN` | "Sesión expirada. Inicia sesión de nuevo." | Redirect to /login |
| `ALREADY_CONFIGURED` | "2FA ya está configurado." | Redirect to /dashboard |
| `INVALID_OTP` | "Código incorrecto, intentá de nuevo." | Clear input, keep focus |
| `MAX_OTP_ATTEMPTS` | "Demasiados intentos. Iniciá sesión de nuevo." | Redirect to /login |
| `SMS_RATE_LIMITED` | "Esperá {N} segundos antes de reenviar." | Show countdown |
| `SMS_DELIVERY_FAILED` | "No se pudo enviar el SMS. Usá un código de respaldo." | Show backup code option |

## Testing Strategy

- **Unit**: OTP input component, backup codes copy, SMS timer
- **Integration**: API calls with mock challenge_token
- **E2E** (Playwright): Full login → 2FA setup → dashboard flow; login → 2FA challenge → dashboard flow
