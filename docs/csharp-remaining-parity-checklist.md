# C# Remaining Parity Checklist

## Scope Guardrails
1. Login/session/auth flow parity is explicitly out of scope for this track.
2. Focus parity only on operator workflows already in use in the JS/Tauri app shell.
3. Backend remains Python API; no contract redesign in this checklist.

## Current Baseline
1. `CSPM-041` is complete (golden parity harness in place).
2. `CSPM-042` is in progress (cross-platform packaging/release hardening).
3. C# CI gates currently pass locally and C# packaging matrix has passed on GitHub runners.

## Remaining Parity Work (Execution Order)

### P0 - Release-Blocking Functional Parity
1. Builder parity audit against production behavior:
   - Verify serial add/remove/complete behavior for all template/size combinations used in production.
   - Validate customer assignment interactions and edge-case messaging.
   - Confirm missing-SIM prompt wording/actions exactly match operator expectation.
2. History parity audit:
   - Validate filter combinations (query + exact + date presets + sort) against JS results.
   - Verify single-pallet detail refresh/delete behavior under API failures.
   - Validate merge-selected export behavior for mixed pallet selections.
3. Spreadsheet editor parity:
   - Verify larger real-world workbook handling (row/column caps, multi-sheet navigation).
   - Confirm save/apply-edits behavior preserves required formulas and protected layout assumptions.

### P1 - Non-Core UX/State Parity
1. Import simulator parity:
   - Validate multi-file upload result reporting against JS behavior for partial failures.
   - Confirm serial search result formatting and no-result messaging.
2. Exports library parity:
   - Validate date range query normalization and open actions across PDF/XLSX.
   - Confirm operator messaging for empty results and invalid input.
3. Customers parity:
   - Validate offline cache fallback behavior across refresh/create/edit/archive cycles.
   - Confirm search + inactive toggle behavior against JS.
4. Settings + Sync Issues parity:
   - Validate sync counters, manual trigger, retry/discard flows under simulated failures.
   - Confirm endpoint test behavior and rollback of temporary probe settings.

### P2 - Hardening and Evidence
1. Add parity fixtures for additional production-like workbook variants.
2. Add scenario evidence snapshots for top operator journeys (before/after state assertions).
3. Link each checklist item to an automated test (unit/integration/parity) or mark explicit manual-only rationale.

## Acceptance Criteria to Close Remaining Parity
1. Every P0 and P1 item has passing automated evidence or approved manual sign-off.
2. No open critical parity defects for Builder/History/Spreadsheet flows.
3. `docs/csharp-parity-golden-matrix.md` and this checklist are both up to date in the same commit.

## Deferred to Release Hardening (Not Parity Scope)
1. Signing/notarization secret provisioning and activation.
2. `csharp-release-stubs` dispatch once workflow exists on default branch.
3. Final release cutover and rollback rehearsals.
