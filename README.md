# agent-office

## Security setup

This repository intentionally ignores local credential files.

Do not commit these files:

- `credentials.json`
- `token.json`
- `pronote_token.json`

Use the provided examples to set up local credentials:

1. Copy `credentials.example.json` to `credentials.json` and fill in your Google OAuth client details.
2. Copy `token.example.json` to `token.json` and paste your local token values.
3. Copy `pronote_token.example.json` to `pronote_token.json` and fill in your Pronote credentials.

If secrets were previously committed, rotate/revoke them immediately:

1. Revoke Google OAuth refresh/access tokens.
2. Regenerate Google OAuth client secret.
3. Change Pronote password and any related credentials.

## Deploy on Render

This app is Render-ready and serves the web UI from FastAPI:

- `/` -> main page
- `/office1` -> homework office
- `/office2` -> website office

### Option A: Blueprint deploy

1. Push this repo to GitHub.
2. In Render, create a new Blueprint and select this repository.
3. Render will use `render.yaml`.
4. Add required secrets in Render environment variables (see below).

### Option B: Manual web service

1. Create a new Render Web Service from this repo.
2. Build command: `pip install -r requirements.txt`
3. Start command: `uvicorn api.server:app --host 0.0.0.0 --port $PORT`
4. Add required secrets in Render environment variables.

### Required Render environment variables

- `ANTHROPIC_API_KEY`
- `PRONOTE_URL`
- `PRONOTE_USERNAME` and `PRONOTE_PASSWORD` (or `PRONOTE_TOKEN_JSON` / `PRONOTE_TOKEN_JSON_B64`)
- `GOOGLE_TOKEN_JSON` (or `GOOGLE_TOKEN_JSON_B64`)

Notes:

- Local files (`token.json`, `pronote_token.json`) still work in local dev.
- On Render, env vars are preferred and already supported by the code.
- Use `.env.example` as the reference template for all values.