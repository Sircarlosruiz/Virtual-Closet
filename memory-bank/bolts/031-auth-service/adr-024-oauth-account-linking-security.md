---
bolt: 031-auth-service
created: 2026-06-10T00:00:00Z
status: accepted
superseded_by: null
---

# ADR-024: OAuth Account Linking Requires Password Confirmation

## Context

When a user logs in with Google OAuth and the Google email matches an existing email+password account, the system must decide how to handle the identity linkage. Allowing automatic linking would enable account takeover: an attacker who gains access to a victim's Google account could link it and bypass the password. Requiring no confirmation would silently merge identities, confusing users who intentionally use the same email for separate accounts.

**Forces**:
- Prevent account takeover via compromised OAuth provider
- Maintain clear user intent for account merging
- Minimize friction for legitimate users who want to link accounts
- Support the common case where a user has one account with email+password and wants to add Google login

## Decision

When a Google OAuth exchange detects an existing email+password account with the same email, the system returns a `requires_account_linking` response to the frontend. The user must enter their existing password to confirm the link. Only after successful password verification is the `OAuthLink` record created, connecting the Google identity to the existing account.

If the user cannot provide the password, they must use email+password login and can link Google from within their account settings (future feature).

## Rationale

Password confirmation is the strongest proof that the person initiating the OAuth link is the legitimate account owner. It prevents account takeover even if the attacker controls the Google account. This pattern is used by major platforms (GitHub, GitLab, AWS) for identity linking.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **Automatic linking** | Zero friction, seamless UX | Account takeover risk if Google account is compromised | Unacceptable security risk |
| **Email verification link** | No password required, proves email access | Slow UX (wait for email), vulnerable if email account is compromised | Password is stronger proof of ownership |
| **Magic link to existing email** | No password needed, one-click | Same vulnerability as email verification — compromised email = account takeover | Does not prove knowledge of existing credentials |
| **Admin-mediated linking** | Highest security | Requires admin intervention, poor UX | Overkill for self-service platform |

## Consequences

### Positive

- Strong protection against account takeover via OAuth
- Clear user intent — user explicitly confirms the link
- Consistent with industry best practices (GitHub, GitLab)
- Audit trail: `OAuthLink.linked_at` records when linking occurred

### Negative

- Friction for users who forgot their password (must reset first)
- Frontend complexity: must handle the linking flow with password input
- Users who registered with Google first and later create email+password with same email will have separate accounts (edge case)

### Risks

- **Password reset abuse**: Attacker triggers password reset to gain access, then links Google. Mitigation: password reset invalidates all refresh tokens (existing policy), and reset email goes to the registered email address.
- **User confusion**: Users may not understand why they need to enter a password after Google login. Mitigation: Clear UI messaging explaining the account linking step.

## Related

- **Stories**: 007-google-oauth-login
- **Standards**: Account linking security policy
- **Previous ADRs**: ADR-018 (challenge token pattern — OAuth exchange returns challenge_token after linking)
