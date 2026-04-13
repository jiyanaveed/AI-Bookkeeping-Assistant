# Deploying the web UI on Vercel

The **backend** (FastAPI, SQLite or Postgres, file uploads, agents) is **not** suited for Vercel serverless. Deploy it on Railway, Render, Fly.io, or a VPS. This guide deploys **only** the static site under `web/` to Vercel.

## Architecture

- **Vercel**: static HTML/CSS/JS from `web/`, same URL paths as local (`/internal/...` via rewrites).
- **Backend**: separate URL; browser calls it via `PUBLIC_API_BASE` (see `web/env.example`).

## Vercel project settings

1. Import the Git repo.
2. **Root Directory**: repository root (where `vercel.json` and `package.json` live).
3. **Framework Preset**: Other (no framework).
4. **Build Command**: `npm run vercel-build` (default from `vercel.json`).
5. **Output Directory**: `web` (default from `vercel.json`).
6. **Install Command**: `npm install` (default; no npm dependencies required).

## Environment variables (Vercel)

| Name | Environment | Required | Description |
|------|-------------|----------|-------------|
| `PUBLIC_API_BASE` | Production (and Preview if you test against a staging API) | **Yes** for split hosting | HTTPS origin of the API, e.g. `https://api.yourdomain.com` (no trailing slash). |

Do **not** add secrets intended for the server (OpenAI, `ADMIN_API_KEY`, database URLs) to Vercel.

## Backend CORS

The API uses permissive CORS in development. For production, restrict `allow_origins` to your Vercel preview and production URLs when you harden the backend.

## Local development

- Run FastAPI as today; UI is served at `http://localhost:8000/internal/...`.
- `runtime-config.js` keeps `API_BASE = ""` so requests stay same-origin.
- Do not commit a production `PUBLIC_API_BASE` into `runtime-config.js`; the Vercel build overwrites it only on the build machine.

## Verification

1. Open `https://<project>.vercel.app/internal/login.html`.
2. Sign up / log in; confirm network calls go to `PUBLIC_API_BASE` (DevTools → Network).

## Choice: frontend-only on Vercel

Use **frontend on Vercel + backend elsewhere** (not full-stack on Vercel). This codebase relies on a long-lived Python process, local/attached disk for uploads, and a database — none of which match Vercel’s serverless model without a full rewrite.
