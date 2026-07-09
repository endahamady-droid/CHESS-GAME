# INFO7 Production Setup

## Render PostgreSQL

1. In Render, create a free PostgreSQL database.
2. Copy its Internal Database URL.
3. In your Web Service, add:

```text
DATABASE_URL=postgresql://...
ADMIN_USERNAME=babba
ADMIN_PASSWORD=change-this-in-production
SESSION_TTL_SECONDS=43200
```

The server runs migrations automatically at startup. It creates/updates:

- `players` with `email`, `elo`, `provider`, `provider_id`, `quiz_level_reached`, `quiz_score`, `games_played`, `twofa_secret`, `twofa_enabled`
- `sessions`
- `rooms`
- `moves`
- `chat_messages`
- `game_history`
- `login_attempts`

With `DATABASE_URL`, accounts, ELO, quiz progress, and match history survive redeploys.

## Two-factor authentication

Social login has been removed. Users can secure the classic username/password login with TOTP 2FA.

Flow:

1. Login with username/password.
2. In Profile, click `Set up 2FA`.
3. Add the manual key to Google Authenticator, Authy, Microsoft Authenticator, or another TOTP app.
4. Enter the 6-digit code to enable 2FA.
5. Future logins require password + authenticator code.

## Security included

- bcrypt password hashes, cost 12
- TOTP 2FA for classic login
- HTTP-only session cookie plus legacy bearer token compatibility
- session expiration
- parameterized SQL queries
- rate limiting for login, register, rooms, chat, and moves
- security headers: CSP, HSTS, frame protection, nosniff, referrer policy
- sanitized username/chat input length limits
- login attempt logging without passwords or tokens

## Recommended Cloudflare setup

1. Add your domain to Cloudflare.
2. Point DNS to Render using a CNAME to your Render hostname.
3. Enable proxied DNS.
4. Turn on WAF managed rules, bot fight mode, and rate limiting for `/api/login`, `/api/register`, `/api/rooms/*/chat`.
5. Keep SSL/TLS mode as Full.

Cloudflare adds network-level DDoS protection before requests reach Render.
