## Pallet Manager 2.0

**Branch:** `develop/2.0`  
**Previous desktop-only version:** see `release/1.1-fallback` branch.

Pallet Manager 2.0 is a **client–server rewrite** of the original 1.1 desktop app.  
It adds a proper backend API, a shared Postgres database, and a React/Tauri desktop UI so multiple stations can work against the same pallets in real time.

### What 2.0 implements

- **Backend API (FastAPI + Postgres + MinIO)**
  - Auth, pallets, customers, barcodes, simulator imports, exports.
  - Schema migrations via Alembic.
  - Object storage integration for PDF exports and raw imports.
- **Modern UI (React + Tauri desktop app)**
  - Live Builder screen for packout operators.
  - History/Barcode search for purchasing.
  - Import Center + Export Library to manage simulator uploads and export artifacts.
  - Shared background login with a single “station” account (no per-user login UI).
- **Multi-station operation**
  - One “Packout Computer” hosts the backend + DB.
  - Additional Windows machines run the desktop EXE and talk to the Packout host over the LAN.
- **Execution backlog and runbooks**
  - Version 2.0 work is tracked in `docs/TASKMASTER_BACKLOG_2_0.md` / `.json`.
  - UAT and rollout plans live in:
    - `docs/UAT_PLAN_PALLET_MANAGER_2_0.md`
    - `docs/ROLLBACK_AND_CUTOVER_PLAN_PALLET_MANAGER_2_0.md`
    - `docs/BACKUP_RESTORE_RUNBOOK.md`
    - `docs/BACKEND_ENVIRONMENT_STRATEGY.md`

---

## Deployment – Pallet Manager 2.0

The recommended production setup:

- **Packout Computer (host)**: runs Docker containers (Postgres + backend API + MinIO).
- **User Computers (2, 3, 4)**: run only the **Windows desktop EXE**, which calls the backend on the Packout Computer over Wi‑Fi.

### 1. Network assumptions

- All machines connect to the same Wi‑Fi / LAN, e.g. **`Crossroads-WiFi`**.
- Packout Computer has a **stable IP** on that network, for example:
  - `10.20.10.62` (your current setup).
- Other machines can reach the host:

```bash
ping 10.20.10.62
```

---

### 2. Backend stack on Packout Computer

**Prerequisites:**

- Docker Desktop (or Docker Engine + docker-compose) installed on Packout.

**Steps:**

- From the project root:

```bash
cd backend
# Ensure FastAPI listens on all interfaces
# APP_HOST=0.0.0.0, APP_PORT=8000 via .env / environment

cd ..
docker compose -f docker-compose.intranet.yml up -d   # or your intranet compose file
```

This should start:

- Postgres
- MinIO (for exports/imports)
- FastAPI backend exposed on `0.0.0.0:8000` → `http://10.20.10.62:8000`.

**Health check (from another machine):**

In a browser on Computer 2/3/4:

```text
http://10.20.10.62:8000/health/live
```

You should see `{"status":"ok"}`.  
If not, open Packout’s firewall for inbound TCP port **8000**.

---

### 3. Building the 2.0 desktop app (Tauri – React/JS UI)

**Important:** The **2.0** app with the JavaScript/React UI is built with **Tauri**, not py2app.  
The Python `setup.py` / py2app build produces the **legacy Tkinter** desktop app (1.1-style).  
To get the **2.0** UI (Live Builder, History, Import Center, etc.), build the Tauri app from `frontend/`.

**Prerequisites:**

- Node.js (LTS)
- Rust: install from [rustup.rs](https://rustup.rs) (or `brew install rust` on macOS)
- No need to install Tauri CLI separately; the project uses `npx tauri` (via `@tauri-apps/cli` in devDependencies).

**Build steps (macOS .app or Windows .exe):**

```bash
cd frontend

# Optional: point the UI at the Packout backend (baked in at build time)
# macOS/Linux:
export VITE_API_BASE_URL=http://10.20.10.62:8000/api/v1
# Windows CMD: set VITE_API_BASE_URL=http://10.20.10.62:8000/api/v1
# Windows PowerShell: $env:VITE_API_BASE_URL = "http://10.20.10.62:8000/api/v1"

npm install
npm run build
npx tauri build
```

- **macOS:** The `.app` bundle is produced under `frontend/src-tauri/target/release/bundle/macos/` (e.g. `Pallet Manager.app`).
- **Windows:** The EXE (and optional NSIS/MSI installers) are under `frontend/src-tauri/target/release/` and `bundle/nsis`, `bundle/msi`. The script `npm run build:desktop` runs `tauri build` and then copies Windows installers to `frontend/dist/installers/`.

The built app has the API base URL baked in and will talk to the configured backend (e.g. `http://10.20.10.62:8000/api/v1`).

---

### 4. Installing the EXE on workstations (Computers 2–4)

On each workstation:

1. Copy the built EXE from the build machine (USB/share).
2. Optionally create a desktop shortcut (rename to `Pallet Manager 2.0`).
3. Make sure the workstation is on `Crossroads-WiFi` and can reach Packout:

   ```bash
   ping 10.20.10.62
   ```

4. Double‑click the EXE:
   - The app will launch.
   - It performs **background login** with the shared account.
   - All calls go to the backend on the Packout Computer.

No Docker/DB/MinIO is needed on Computers 2–4.

---

## Local development (2.0)

### Backend (FastAPI)

- See `backend/README.md` for details.
- Quick start:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # or .venv\Scripts\activate on Windows
pip install -e .
uvicorn app.main:app --reload --port 8000
```

Run migrations:

```bash
cd backend
alembic upgrade head
```

Environment setup:

- Copy `.env.example` → `.env` and fill in DB, JWT, MinIO settings.  
- See `docs/BACKEND_ENVIRONMENT_STRATEGY.md` for the full matrix.

### Frontend (React + Vite + Tauri)

```bash
cd frontend
npm install

# For dev against a local backend:
set VITE_API_BASE_URL=http://localhost:8000/api/v1
npm run dev
```

To run Playwright UI smoke tests:

```bash
cd frontend
VITE_API_BASE_URL=http://localhost:8000/api/v1 npx playwright test
```

---

## Branches and legacy 1.1

- **`develop/2.0`**: active Pallet Manager 2.0 development (this README).
- **`main`**: mainline; will eventually track stable 2.0 once cutover is complete.
- **`release/1.1-fallback`**: legacy Python/Tkinter desktop app (version 1.1).
  - Old `app/pallet_builder_gui.py` UI and installer scripts live there.

For 1.1‑specific docs (Excel folders, standalone installers, etc.), see the `release/1.1-fallback` branch. This branch focuses on the 2.0 client–server architecture and deployment. 
