# Deploy on Railway

`docker-compose.prod.yml` is the reference stack. On Railway each compose service becomes one Railway service. Local dev stays on `docker-compose.yml`.

## Services

| Railway service | Source | Notes |
|---|---|---|
| `backend` | repo, root dir `backend/`, Dockerfile target `prod` | Listens on `$PORT` (Railway sets it). Health check path `/health`. Attach a volume at `/cache/fastembed` so models are not re-downloaded on each deploy. |
| `frontend` | repo root, Dockerfile path `frontend/Dockerfile` | Static build served by nginx on `$PORT`. Set `VITE_API_URL` as a variable (Railway passes it as a build arg). |
| `postgres` | Railway PostgreSQL plugin | Use its `DATABASE_URL`. |
| `qdrant` | Docker image `qdrant/qdrant:v1.15.4` | Volume at `/qdrant/storage` (required). Set Qdrant service API key via env. Keep it on the private network. |

## Variables

Copy `.env.example` into Railway variables. Never commit real values.

For local `docker-compose.prod.yml`, put credentials only in `.env` (the compose file does not embed them). Postgres reads its credentials from that env file.

Backend:
- `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `ZAI_API_KEY`
- `INTERNAL_TOKEN`: long random string
- `DATABASE_URL`: `${{Postgres.DATABASE_URL}}`
- `QDRANT_URL`: `http://qdrant.railway.internal:6333`
- `QDRANT_API_KEY`: same value as Qdrant's service API key
- `FASTEMBED_CACHE_PATH=/cache/fastembed`

Frontend:
- `VITE_API_URL`: public backend URL, e.g. `https://daleelai-backend.up.railway.app`. It is baked in at build time, so redeploy the frontend after changing it.

CORS: `backend/config/settings.yaml` `cors_origins` lists only localhost origins today. Add the public frontend URL there before the browser can call the API.

## Health check

`GET /health` on the backend returns 200 when the app is up. Set it as the Railway health check path.

## Qdrant `documents` collection

Holds about 18.6k points. **Never delete or rebuild it casually.** Rebuilding re-runs the whole ingestion pipeline. Take a snapshot before any Qdrant upgrade, volume change, or reindex.

Snapshot (from a machine that can reach Qdrant):

```sh
curl -X POST -H "api-key: $QDRANT_API_KEY" "$QDRANT_URL/collections/documents/snapshots"
curl -H "api-key: $QDRANT_API_KEY" "$QDRANT_URL/collections/documents/snapshots"   # list names
curl -H "api-key: $QDRANT_API_KEY" -o documents.snapshot \
  "$QDRANT_URL/collections/documents/snapshots/<name>"
```

Restore into a new or empty Qdrant:

```sh
curl -X POST -H "api-key: $QDRANT_API_KEY" \
  -F "snapshot=@documents.snapshot" \
  "$QDRANT_URL/collections/documents/snapshots/upload?priority=snapshot"
curl -H "api-key: $QDRANT_API_KEY" "$QDRANT_URL/collections/documents"   # check points_count ≈ 18.6k
```

To seed Railway from local data: take the snapshot from local Qdrant (`http://localhost:6333`, no key), then upload it to Railway Qdrant (temporarily expose it or run the upload from a Railway shell).

## Local check of the prod stack

```sh
cp .env.example .env   # fill keys
docker compose -f docker-compose.prod.yml up --build
# API http://localhost:8000/health, app http://localhost:8080
```
