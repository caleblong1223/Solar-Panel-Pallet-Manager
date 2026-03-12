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
VITE_PRIMARY_API_BASE_URL=http://127.0.0.1:8001/api/v1
VITE_FALLBACK_API_BASE_URL=http://127.0.0.1:8010/api/v1
```

If `VITE_PRIMARY_API_BASE_URL` is not set, the app falls back to `VITE_API_BASE_URL` for backward compatibility.

## Runtime Server Settings

- The app now supports runtime backend configuration from the in-app `Settings` screen (`/settings`).
- Saved settings are stored locally and override `VITE_API_BASE_URL` for API requests.
- Settings include:
  - `Primary API Base URL (Central Server)`
  - `Fallback API Base URL (Local Device)` (optional)
- API calls will try primary first, then fallback on network timeout/unreachable/server-5xx failures.

## Offline Queue Foundation

- Builder mutations now use a repository layer with local fallback.
- Offline mutations are written to a local outbox queue (`localStorage`) for later replay.
- A background sync engine now replays queued operations when connectivity is restored.
- Replays send `X-Client-Operation-Id` so backend can dedupe duplicate mutation attempts.
- Sync status is surfaced in navigation/settings, and unresolved conflicts are listed in `/sync-issues` for operator action.
- Backend conflict responses now include machine-readable `error_code` values, and Sync Issues displays remediation hints per code.

## Tauri

`src-tauri/tauri.conf.json` is scaffolded for desktop integration.

## Windows Installer Build

Use the dedicated Windows batch file:

```bat
cd frontend
scripts\build-tauri-windows-installer.bat
```

This script:

- runs `npm install`
- runs `npm run build:desktop`
- builds the Tauri app
- copies the supported Windows MSI installer into `frontend\dist\installers`

Default build-time API URLs used by the batch file:

```bat
VITE_PRIMARY_API_BASE_URL=http://10.20.10.100:8001/api/v1
VITE_FALLBACK_API_BASE_URL=http://127.0.0.1:8010/api/v1
```

Override them in the same CMD session before running the script if needed:

```bat
set VITE_PRIMARY_API_BASE_URL=http://10.20.10.62:8001/api/v1
set VITE_FALLBACK_API_BASE_URL=http://127.0.0.1:8010/api/v1
scripts\build-tauri-windows-installer.bat
```

Supported Windows installer output path:

- `frontend\dist\installers\Pallet Manager_2.0.0_x64_en-US.msi`

Do not distribute the NSIS `.exe` installer for this app. Use the MSI build for Windows releases because the bundled backend works correctly from the MSI install.
