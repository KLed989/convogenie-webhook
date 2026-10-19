# Convogenie webhook starter (test-only)

This is a public webhook receiver for testing delivery from Convogenie. It does
**not** save leads and does **not** connect to the CRM yet.

## Endpoints

- `GET /` — service status
- `GET /health` — health check
- `POST /webhook` — authenticated JSON receiver

## Authentication

Send the shared secret in the `X-Webhook-Secret` HTTP header. Configure the
same secret in Render and in Convogenie's webhook configuration, if Convogenie
supports custom headers. If Convogenie uses a different authentication
mechanism, adapt this before use.

## Render settings

- Runtime: Python
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Environment variable: `CONVOGENIE_API_KEY` = a long random secret

## Test request

```bash
curl -i -X POST "https://YOUR-SERVICE.onrender.com/webhook" \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: YOUR_SECRET" \
  -d '{"event":"test","lead":{"name":"Sample Lead","email":"sample@example.com"}}'
```

Expected response is HTTP `202` and JSON that explicitly says `persisted: false`.
A `202` only means the test request was accepted by this process, not saved.

Do not use this test-only starter for production leads. Add durable storage,
provider signature verification/replay protection, and CRM integration before
relying on it for real leads.
