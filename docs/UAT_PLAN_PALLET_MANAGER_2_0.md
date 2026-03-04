# Pallet Manager 2.0 - UAT Plan (PM2-072)

## Purpose

This document supports **PM2-072 – UAT with packout and purchasing workflows** by defining:

- Concrete UAT test cases for each role.
- Preconditions and environments.
- Pass/fail criteria and sign-off checklist.

## 1. Environments & Preconditions

- **Backend**: Pallet Manager API running against a QA/Postgres instance containing migrated legacy data.
- **Frontend**: Tauri desktop build or Vite app pointed at the QA API.
- **Auth**:
  - At least one `packout_operator` user.
  - At least one `purchasing_manager` user.
  - An `admin` user for administrative actions.
- **Data**:
  - Representative customers and pallets from migration.
  - At least one completed pallet with exports.
  - At least one simulator import batch with PASS/FAIL rows.

## 2. Packout (Builder) UAT Scenarios

**Goal**: A packout operator can complete pallet build workflows without falling back to legacy tools.

### P1 – Start and complete a pallet

- Steps:
  - Login as `packout_operator`.
  - Navigate to **Builder**.
  - Create a new pallet (set template, capacity).
  - Add serials until pallet is full.
  - Complete pallet.
- Expected:
  - Status transitions from `active` → `completed`.
  - Capacity and remaining counts update correctly.

### P2 – Prevent duplicates and overfill

- Steps:
  - With an active pallet, add a serial.
  - Attempt to add the same serial again (case-variant).
  - Attempt to add more serials than capacity.
- Expected:
  - Duplicate and overflow attempts are rejected with clear error messages.

### P3 – Admin-only resets/deletes

- Steps:
  - As `packout_operator`, attempt to reset or delete a completed pallet.
  - As `admin`, reset and then delete a completed pallet.
- Expected:
  - Packout is forbidden (403).
  - Admin can successfully reset and delete.

## 3. Purchasing (History & Search) UAT Scenarios

**Goal**: Purchasing can reliably locate pallets and exports by serial and metadata.

### C1 – Barcode search

- Steps:
  - Login as `purchasing_manager`.
  - Use **History/Barcode search** to look up a known serial (exact and partial).
- Expected:
  - Results include pallet and simulator sources when applicable.
  - Exact match flag behaves as designed.

### C2 – History explorer navigation

- Steps:
  - From history UI, filter by customer/date/serial where data exists.
  - Open a pallet detail and verify associated exports.
- Expected:
  - Filters return correct counts.
  - Drill-down view shows accurate pallet and export metadata.

## 4. Import/Export UAT Scenarios

**Goal**: Simulator import and export library flows behave as described in PRD/TDD.

### I1 – Import center

- Steps:
  - Login as `packout_operator` or `admin`.
  - Upload a valid simulator CSV/XLSX file.
  - Observe batch status and row counts.
  - Fetch the batch by ID.
- Expected:
  - Batch moves to `completed` (or `failed` with clear reason).
  - Row counts (imported/rejected/total) are correct.

### E1 – Export creation and open

- Steps:
  - With a completed pallet, create an export from **Import/Export** UI.
  - Filter export library by pallet ID.
  - Open an export via generated URL.
- Expected:
  - Export is created only for valid completed pallets.
  - Export appears in the list and opens via browser/PDF viewer.

## 5. Sign-off Checklist

- **Packout UAT**:
  - [ ] P1 – Basic pallet lifecycle passes.
  - [ ] P2 – Duplicate/overflow protections confirmed.
  - [ ] P3 – Admin/packout role separation confirmed.
- **Purchasing UAT**:
  - [ ] C1 – Barcode search (exact and partial) validated.
  - [ ] C2 – History explorer filters and details validated.
- **Import/Export UAT**:
  - [ ] I1 – Simulator import and batch inspection validated.
  - [ ] E1 – Export creation and open validated.
- **Global**:
  - [ ] No Sev-1 or Sev-2 issues open for these flows.
  - [ ] Packout lead sign-off (name/date):
  - [ ] Purchasing lead sign-off (name/date):

