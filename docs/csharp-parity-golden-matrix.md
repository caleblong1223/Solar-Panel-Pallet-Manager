# C# UI Parity Golden Matrix

## Purpose
This document defines the behavior-level parity evidence required for Pallet Manager 2.0 C# before release promotion.

## Scope
- Track: `develop/2.0-csharp`
- Baseline reference: current JS/Tauri behavior on `develop/2.0`
- Verification type: automated parity tests + fixture-based assertions

## High-Risk Areas
1. Builder missing-SIM decision branches and outbox payload semantics
2. History filter semantics + merge export behavior
3. Spreadsheet open/edit/save roundtrip (cell-level and formula preservation)
4. Offline queue durability and replay ordering
5. Settings endpoint probe safety (temporary test values must not persist)

## Golden Scenario Matrix
| Scenario ID | Risk Area | Parity Contract | Evidence |
| --- | --- | --- | --- |
| PAR-CORE-001 | Builder | Missing SIM prompt opens for absent SIM serial; reject keeps list unchanged; accept fallback enqueues `allow_missing_sim_data=true`. | `CoreFlowsParityTests.Builder_MissingSimDecisionJourney_PreservesQueueSemantics` |
| PAR-CORE-002 | Builder | SIM-present add/remove/complete preserves slot reindexing and expected outbox operation types. | `CoreFlowsParityTests.Builder_SimDataPresentJourney_AddRemoveComplete_PreservesSlotParity` |
| PAR-CORE-004 | Builder | Selected template + pallet-size matrix (200WT/220WT/220M6/330WT/450WT/450BT x 25/26/30/35) must be preserved in create payload across start/add/complete flow. | `CoreFlowsParityTests.Builder_TemplateAndSizeMatrix_UsesSelectedValuesInCreatePayload` |
| PAR-CORE-003 | History | Refresh/filter/merge/open export workflow remains behaviorally identical for operator-visible actions. | `CoreFlowsParityTests.History_RefreshFilterMergeAndOpenExport_MatchesExpectedFlow` |
| PAR-NONCORE-001 | Customers | Display name validation error parity for empty create/update submission. | `NonCoreFlowsParityTests.Customers_SaveWithoutDisplayName_ShowsParityValidationMessage` |
| PAR-NONCORE-002 | Customers | Create/search/archive journey keeps active/inactive listing parity. | `NonCoreFlowsParityTests.Customers_CreateSearchArchive_JourneyMaintainsParityState` |
| PAR-NONCORE-003 | Import | Blank serial search validation parity. | `NonCoreFlowsParityTests.Import_SearchWithBlankSerial_ShowsParityValidationMessage` |
| PAR-NONCORE-004 | Import | Upload failure path summarizes per-file failures and aggregate counts. | `NonCoreFlowsParityTests.Import_UploadWhenAllCandidatesFail_ShowsFailedSummary` |
| PAR-NONCORE-005 | Exports | Invalid pallet number validation parity. | `NonCoreFlowsParityTests.Exports_SearchWithInvalidPalletNumber_ShowsParityValidationMessage` |
| PAR-NONCORE-006 | Exports | Invalid date handling omits bad query fields while preserving valid boundary. | `NonCoreFlowsParityTests.Exports_SearchWithInvalidDate_OmitsDateFiltersFromQuery` |
| PAR-NONCORE-007 | Settings | Primary endpoint probe failure cannot persist temporary test URL. | `NonCoreFlowsParityTests.Settings_TestPrimaryProbeFailure_DoesNotPersistTemporaryEndpoint` |
| PAR-NONCORE-008 | Settings | Saved configuration remains canonical after temporary probe failure. | `NonCoreFlowsParityTests.Settings_SaveThenPrimaryTestFailure_PreservesSavedConfiguration` |
| PAR-XLSX-001 | Spreadsheet | Golden CSV shape remains stable for baseline parser assumptions. | `ExportSpreadsheetParityTests.GoldenCsvFixture_ParsesWithExpectedShape` |
| PAR-XLSX-002 | Spreadsheet | Golden workbook edit roundtrip preserves full cell matrix parity. | `ExportSpreadsheetParityTests.GoldenXlsxRoundtrip_AfterEdit_MatchesExpectedFixtureAtCellLevel` |
| PAR-XLSX-003 | Spreadsheet | Production-like workbook preserves formulas and expected edited cells. | `ExportSpreadsheetParityTests.ProductionLikeWorkbook_AfterEdit_MatchesExpectedCellContracts_AndPreservesFormulas` |

## Fixture Inventory
- `csharp/tests/PalletManager.ParityTests/Fixtures/exports/export_golden.csv`
- `csharp/tests/PalletManager.ParityTests/Fixtures/exports/export_golden_expected_after_edit.csv`
- `csharp/tests/PalletManager.ParityTests/Fixtures/exports/production_like_expected_after_edit.cells`

## Release Gate Criteria
1. Integration tests pass.
2. Unit tests pass.
3. Parity test suite passes with no skipped parity cases.
4. No failing scenario IDs in this matrix.

## Gate Commands
```bash
bash csharp/scripts/ci-gate.sh
```

Optional parity-only run:
```bash
dotnet test csharp/tests/PalletManager.ParityTests/PalletManager.ParityTests.csproj -nologo
```

## Sign-Off Notes
- This matrix is the parity source of truth for `CSPM-041`.
- Any behavior change in C# must update both parity tests and this matrix before merge.
