# Frontend (Tauri + React)

## Dev (web only)

```bash
cd frontend
npm install
npm run dev
```

## Environment

Create `.env` with:

```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## Runtime Server Settings

- The app now supports runtime backend configuration from the in-app `Settings` screen (`/settings`).
- Saved settings are stored locally and override `VITE_API_BASE_URL` for API requests.
- If the backend is unavailable during startup, the app can initialize into offline mode when a cached user profile exists.

## Offline Queue Foundation

- Builder mutations now use a repository layer with local fallback.
- Offline mutations are written to a local outbox queue (`localStorage`) for later replay.
- Current implementation provides queueing + visibility; replay-to-server logic is scaffolded for the next step.

## Tauri

`src-tauri/tauri.conf.json` is scaffolded for desktop integration.
