# Deploying to Cloud Run (project `ctoteam`)

The app ships as **one container**: a multi-stage build compiles the Vite
frontend and FastAPI serves it alongside `/api`, so the browser sees a single
origin and CORS never enters the picture.

## Status: DEPLOYED (2026-10-06)

**URL:** https://tableau-analyzer-1035117862188.asia-south1.run.app

Region is **asia-south1**. The org policy `constraints/gcp.resourceLocations`
on this project permits only `asia-south1` and `us-central1`; the first deploy
attempt to `asia-southeast1` (the gcloud default on the dev machine) failed
validation with `FAILED_PRECONDITION`.

### Roles held by the deploying account

On project `ctoteam`, `madhu.vamsituraka@mastechdigital.com` was granted:

| Role | Why |
|---|---|
| `roles/run.admin` | Create and update the Cloud Run service |
| `roles/iam.serviceAccountUser` | Deploy as the runtime service account |
| `roles/serviceusage.serviceUsageAdmin` | Enable the APIs below (skip if the owner enables them) |
| `roles/artifactregistry.admin` | `run deploy --source` creates the image repo on first run |
| `roles/iap.admin` | Turn on IAP and grant the Mastech domain |

APIs enabled: `run`, `cloudbuild`, `artifactregistry`, `iap`.

### Verified after deploy

- Container starts clean: `Uvicorn running on 0.0.0.0:8080`, startup probe
  passed, no errors in the revision log.
- Anonymous GET `/` returns **302** to `accounts.google.com` — IAP is gating
  the service, including `/api/*`.
- Not verifiable from the CLI: the signed-in experience. IAP intercepts every
  path (even `gcloud run services proxy`), so the SPA render and an authorised
  `/api/health` need a real browser login by a Mastech account.

## Deploy

```
./deploy.sh
```

Overridable: `PROJECT`, `REGION` (default `asia-southeast1`), `SERVICE`.

Access model: the service is deployed `--no-allow-unauthenticated` and sits
behind IAP, with `domain:mastechdigital.com` granted
`roles/iap.httpsResourceAccessor`. Mastech staff get a Google sign-in page;
everyone else is refused at the proxy, before reaching the app.

## Known limits of this deployment

1. **`--max-instances=1`.** The job store (`app/jobs/store.py`) is a
   process-local dict, so a second instance cannot see a workbook uploaded to
   the first. Raising this requires moving job state to GCS or Redis.
2. **Uploads cap at 32 MiB**, not the 500 MB in `core/config.py` â€” that is a
   Cloud Run HTTP/1 request-body limit, and oversized files fail at the proxy
   with a 413 before FastAPI sees them. Fixing it properly means uploading to
   GCS via signed URLs.
3. **AI features are inert.** `anthropic` is a lazy optional import and is not
   in `requirements.txt`, so DAX suggestion, AI review, and PBIP LLM translate
   fail even with a valid pasted key. Add `anthropic` to `requirements.txt` to
   enable them.
