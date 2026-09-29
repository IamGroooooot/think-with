---
max_turns: 8
timeout_seconds: 180
allowed_tools: [Skill, Read]
runs: 3
---
/think-with:lay-out Our web login uses OAuth Authorization Code with PKCE through a backend-for-frontend. Show me what passes between the browser, our BFF, and the IdP, and where the tokens end up.

Setup:
- The SPA is served from app.example.com. The BFF is api.example.com. The IdP is Auth0.
- "Log in" sends the browser to `api.example.com/login`. The BFF creates a PKCE `code_verifier` and a `state`, stores both in a short-lived Redis entry keyed by a temporary cookie, and redirects the browser to Auth0 `/authorize` with `code_challenge` and `state`.
- After the user signs in, Auth0 redirects the browser to `api.example.com/callback?code=…&state=…`.
- The BFF checks `state`, then calls Auth0 `/oauth/token` server-to-server with the code, the `code_verifier`, and its client secret. It receives an access token (15 min), a refresh token, and an ID token.
- The BFF stores all three tokens in a Redis session and sets an HttpOnly, Secure, SameSite=Lax cookie `sid` on the browser, then redirects to app.example.com.
- The SPA calls `api.example.com/api/*` with the cookie. The BFF looks up the session, refreshes the access token if it expired, and forwards the request to internal services with `Authorization: Bearer <access token>`.
