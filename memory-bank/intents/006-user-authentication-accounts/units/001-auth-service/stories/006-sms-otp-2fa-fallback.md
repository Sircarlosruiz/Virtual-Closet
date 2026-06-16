---
id: 006-sms-otp-2fa-fallback
unit: 001-auth-service
intent: 006-user-authentication-accounts
status: complete
priority: must
created: 2026-06-08T00:00:00.000Z
assigned_bolt: null
implemented: true
---

# Story: 006-sms-otp-2fa-fallback

## User Story

**As a** mayorista who prefers SMS over an authenticator app
**I want** to receive a one-time code via SMS to complete 2FA
**So that** I can access the platform without an authenticator app

## Acceptance Criteria

- [ ] **Given** I am on the 2FA setup screen, **When** I choose SMS as my 2FA method and provide a valid phone number, **Then** an OTP is sent to my phone and I am prompted to confirm it
- [ ] **Given** I submit the correct 6-digit OTP within 5 minutes, **When** setup is confirmed, **Then** SMS 2FA is saved as my method with the phone number stored and backup codes are generated
- [ ] **Given** SMS is my 2FA method and I have a valid `challenge_token`, **When** I request the SMS OTP during login, **Then** a 6-digit code is sent to my registered phone
- [ ] **Given** I submit the correct OTP within 5 minutes, **When** the challenge is validated, **Then** I receive access + refresh tokens
- [ ] **Given** I exceed 3 SMS OTP requests in 10 minutes, **When** I request another, **Then** I receive "Rate limit exceeded; try again in X minutes"
- [ ] **Given** I choose "Use backup code" on the SMS challenge screen, **When** I submit a valid backup code, **Then** login succeeds and that code is consumed

## Technical Notes

- SMS provider: Twilio (configurable via env)
- OTP: 6-digit numeric, generated via `secrets.randbelow(10**6)`, stored hashed in Redis with 5-min TTL
- Send OTP endpoint: `POST /auth/2fa/sms/send` (requires `challenge_token`)
- Verify OTP endpoint: `POST /auth/2fa/sms/verify` (OTP code + `challenge_token`)
- Rate limiting: Redis counter per `user_id`, window 10 minutes, max 3 sends
- Phone number stored encrypted in `TwoFactorConfig`

## Dependencies

### Requires
- 003-login-email-password

### Enables
- 009-jwt-session-management

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| OTP expired (>5 min) | New SMS must be requested; old OTP invalid |
| SMS delivery fails (Twilio error) | Error surfaced to user; suggest using backup codes |
| Invalid phone number format at setup | Validation error before SMS is sent |

## Out of Scope

- Changing 2FA method post-setup (future intent)
- Voice call fallback
