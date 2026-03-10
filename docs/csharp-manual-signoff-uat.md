# C# Manual Sign-Off UAT (Parity Closure)

## Purpose
This runbook closes the remaining manual parity items on `develop/2.0-csharp`.

## Preconditions
1. Latest `develop/2.0-csharp` build is installed for tester platform.
2. Backend API is reachable and seeded with representative data.
3. `bash csharp/scripts/ci-gate.sh` is green for the tested commit.
4. Tester has access to at least one production-like simulator import file and one production-like workbook export.

## Manual Sign-Off Cases

### MS-001 Builder Customer Assignment + Missing-SIM Operator Copy
1. Open Builder.
2. Start a new pallet with:
   - panel type `220WT`
   - pallet size `25`
   - explicit customer assignment
3. Add one known valid serial (sim data present).
4. Add one serial with no sim data.
5. Verify missing-SIM prompt wording and action labels are operator-acceptable.
6. Choose reject path once and confirm item is not added.
7. Re-add same serial and choose fallback path.
8. Complete pallet flow.

Expected results:
1. Customer assignment persists for the active build flow.
2. Missing-SIM prompt wording is clear and operationally acceptable.
3. Reject path keeps serial off pallet; fallback path adds serial with fallback semantics.
4. No unexpected warnings/errors in normal path.

Evidence capture:
1. Screenshot of prompt text and buttons.
2. Screenshot of Builder summary after reject and after fallback.
3. Tester notes with explicit “copy approved” or “copy change required”.

### MS-002 Spreadsheet Production Workbook Spot-Check
1. Open History and select a pallet with production-like workbook export.
2. Open spreadsheet editor for XLSX export.
3. Verify multi-sheet navigation works.
4. Edit one non-formula data cell and save.
5. Re-open workbook and verify edited value persisted.
6. Verify representative formula cells remained formulas.

Expected results:
1. Workbook opens without corruption.
2. Edit/save/reopen cycle succeeds.
3. Formula-bearing cells are still formulas and layout assumptions remain valid.

Evidence capture:
1. Original workbook filename and export ID.
2. Before/after screenshots of edited cell.
3. Screenshot or note proving formula cells remained formulas.

### MS-003 Import Progress UX Acceptance
1. Open Import Sun Simulator Data.
2. Select one medium-sized import file and start upload.
3. Observe progress bar and progress text during transfer.
4. Repeat with two files (one expected success, one expected failure).

Expected results:
1. Progress bar moves from `0` to `100`.
2. Progress text communicates current stage clearly.
3. Final status summarizes imported/failed counts correctly.
4. Per-file rows remain understandable to operators.

Evidence capture:
1. Screenshot during upload progress.
2. Screenshot after completion with summary + per-file rows.
3. Tester notes: “progress UX accepted” or specific wording/behavior issues.

## Sign-Off Record
| Case ID | Tester | Date (YYYY-MM-DD) | Result (Pass/Fail) | Notes |
| --- | --- | --- | --- | --- |
| MS-001 |  |  |  |  |
| MS-002 |  |  |  |  |
| MS-003 |  |  |  |  |

## Closure Rule
1. All three cases must be `Pass` for manual parity closure.
2. Any `Fail` must create a follow-up fix task and block parity close.
