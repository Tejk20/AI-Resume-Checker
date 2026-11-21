# HireLens AI password recovery

Signup and sign-in link to `/forgot-password`. A successful request queues a reset email for a matching account, without revealing whether the address is registered. `/reset-password` accepts a link from that email and lets the user set a new password.

## Email activation on the existing free host

The implementation uses Brevo's HTTPS transactional-email API through the existing `httpx` dependency. It does not need SMTP ports or a new Python SDK. No paid service is provisioned by this code.

1. Sign up at <https://onboarding.brevo.com/account/register> and select the **Free** plan. Verify your account and complete any required account/transactional-sending approval.
2. In **Settings → Senders, Domains, IPs → Senders**, add a sender named **HireLens AI** and an email address you control. Complete sender verification. A verified custom domain gives better deliverability. Brevo documents temporary rewriting of unauthenticated/free-address senders; do not assume permanent delivery support or inbox placement for those addresses.
3. In Brevo's **SMTP & API → API Keys**, create an API key for this application. Keep it secret.
4. In Render, open the existing app → **Environment**, and add:

   | Key | Value |
   |---|---|
   | `BREVO_API_KEY` | Your actual private Brevo API key |
   | `PASSWORD_RESET_SENDER` | The sender email verified in Brevo |
   | `PUBLIC_ORIGIN` | `https://avom-resume-checker.onrender.com` (already configured) |

5. Save/redeploy. Do not put these credentials in GitHub, a browser screenshot, or chat.
6. Request a link for an account you control. Confirm receipt and test setting a new password. Until sender configuration is present, the API returns a clear 503 rather than claiming that mail was sent.

Brevo currently documents 300 sends/day on its Free plan. Account approval, sender verification, provider limits and deliverability still apply. Do not select a paid plan without authorization.

## API

| Endpoint | Request | Result |
|---|---|---|
| `POST /api/v1/auth/forgot-password` | `{email}` | 202 with a generic conditional message; 503 if sending is unconfigured |
| `POST /api/v1/auth/reset-password` | `{token,password}` | Password update; 400 for expired, invalid or used token; validation requires 10–128 password characters |

The reset link puts the token in the URL **fragment**, for example `/reset-password#token=...`. Fragments are not sent in HTTP requests or referrer headers. React captures the token into memory and removes the fragment from the current browser-history entry. A page reload after that requires reopening the email link. The app never offers a public token-display endpoint.

Only a SHA-256 digest of a random 32-byte token is stored. Tokens expire after 30 minutes and can be redeemed once. A new request invalidates the account's earlier links. Conditional database UPDATE claims the token atomically; hashing/transaction failure rolls back the claim. A successful reset updates the PBKDF2 password hash and revokes all account sessions. The user signs in again; resetting does not automatically create a new session.

The configured public origin controls links; untrusted request Host headers do not. Existing request-origin checks, password rules and account attempt limits apply. Email-provider errors are logged by exception type, without keys, reset URLs or provider response bodies. Generic 202 acceptance does not guarantee that an upstream mail provider ultimately delivered the message. There is no durable retry queue; provider/account failures require checking logs and requesting a new link.

## Verification

Five recovery API tests cover missing sender configuration, hashed storage, single-use redemption, session revocation, generic responses, expiry, replacement and rollback/retry. Four frontend tests cover link requests, unavailable delivery, resetting via a fragment token and missing-link handling. Unit tests mock email delivery and never send real messages.

Live email delivery remains unverified until a real sender is configured and a requested test email is received. This is separate from successful automated account/reset tests.

## References

- [Brevo Free plan](https://help.brevo.com/hc/en-us/articles/208580669-FAQs-What-are-the-limits-of-the-Free-plan)
- [Create a sender](https://help.brevo.com/hc/en-us/articles/208836149-Create-a-new-sender-From-name-and-From-email)
- [Brevo transactional-email API](https://developers.brevo.com/reference/send-transac-email)
- [Brevo sender requirements and temporary rewriting](https://help.brevo.com/hc/en-us/articles/14925263522578-Comply-with-Gmail-Yahoo-and-Microsoft-s-requirements-for-email-senders)
- [OWASP forgot-password guidance](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html)
