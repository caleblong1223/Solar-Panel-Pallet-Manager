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
   - Status: in progress. Automated matrix evidence now exists in `CoreFlowsParityTests.Builder_TemplateAndSizeMatrix_UsesSelectedValuesInCreatePayload`.
   - Validate customer assignment interactions and edge-case messaging.
   - Confirm missing-SIM prompt wording/actions exactly match operator expectation.
2. History parity audit:
   - Validate filter combinations (query + exact + date presets + sort) against JS results.
   - Verify single-pallet detail refresh/delete behavior under API failures.
   - Validate merge-selected export behavior for mixed pallet selections.
   - Status: in progress. Automated evidence added in `CoreFlowsParityTests.History_FilterComboAndSort_MatchesExpectedRows` and `CoreFlowsParityTests.History_DeleteAndMergeFailures_SetOperatorSafeMessages`.
3. Spreadsheet editor parity:
   - Verify larger real-world workbook handling (row/column caps, multi-sheet navigation).
   - Confirm save/apply-edits behavior preserves required formulas and protected layout assumptions.
   - Status: in progress. Automated evidence added in `CoreFlowsParityTests.History_SpreadsheetEditor_LargeWorkbookCapsAndMultiSheetNavigation_MatchesExpectedFlow` plus `ExportSpreadsheetParityTests.*` formula/cell contract checks.

### P1 - Non-Core UX/State Parity
1. Import simulator parity:
   - Validate multi-file upload result reporting against JS behavior for partial failures.
   - Confirm serial search result formatting and no-result messaging.
   - Status: in progress. Automated evidence added in `NonCoreFlowsParityTests.Import_UploadWithMixedResults_ShowsPartialFailureSummary`, `NonCoreFlowsParityTests.Import_SearchNoResults_ShowsParityNoDataMessage`, and `ImportSimulatorViewModelTests.UploadAsync_ShowsProgressAndPrioritizesInSpecMostRecentRows`.
2. Exports library parity:
   - Validate date range query normalization and open actions across PDF/XLSX.
   - Confirm operator messaging for empty results and invalid input.
   - Status: in progress. Automated evidence added in `NonCoreFlowsParityTests.Exports_OpenPdfAndXlsx_UsesSystemLauncherEndpoints` and `NonCoreFlowsParityTests.Exports_SearchNoResults_ShowsEmptyStateMessage`.
3. Customers parity:
   - Validate offline cache fallback behavior across refresh/create/edit/archive cycles.
   - Confirm search + inactive toggle behavior against JS.
   - Status: in progress. Automated evidence added in `NonCoreFlowsParityTests.Customers_OfflineFallback_RespectsSearchAndInactiveToggle`.
4. Settings + Sync Issues parity:
   - Validate sync counters, manual trigger, retry/discard flows under simulated failures.
   - Confirm endpoint test behavior and rollback of temporary probe settings.
   - Status: in progress. Automated evidence added in `NonCoreFlowsParityTests.SettingsAndSyncIssues_ManualTriggerAndRetryDiscard_MaintainParityFlow` plus existing endpoint rollback tests.

### P2 - Hardening and Evidence
1. Add parity fixtures for additional production-like workbook variants.
2. Add scenario evidence snapshots for top operator journeys (before/after state assertions).
3. Link each checklist item to an automated test (unit/integration/parity) or mark explicit manual-only rationale.

## Evidence Ledger (Automated vs Manual)
1. Builder
   - Automated: `CoreFlowsParityTests.Builder_MissingSimDecisionJourney_PreservesQueueSemantics`, `CoreFlowsParityTests.Builder_SimDataPresentJourney_AddRemoveComplete_PreservesSlotParity`, `CoreFlowsParityTests.Builder_TemplateAndSizeMatrix_UsesSelectedValuesInCreatePayload`.
   - Manual sign-off required: customer assignment interaction parity and operator copy/tone parity for missing-SIM prompt in live workflow.
2. History
   - Automated: `CoreFlowsParityTests.History_RefreshFilterMergeAndOpenExport_MatchesExpectedFlow`, `CoreFlowsParityTests.History_FilterComboAndSort_MatchesExpectedRows`, `CoreFlowsParityTests.History_DeleteAndMergeFailures_SetOperatorSafeMessages`.
   - Manual sign-off required: none currently identified.
3. Spreadsheet
   - Automated: `ExportSpreadsheetParityTests.*`, `CoreFlowsParityTests.History_SpreadsheetEditor_LargeWorkbookCapsAndMultiSheetNavigation_MatchesExpectedFlow`.
   - Manual sign-off required: production workbook spot-check on operator-selected samples.
4. Import simulator
   - Automated: `NonCoreFlowsParityTests.Import_*`, `ImportSimulatorViewModelTests.UploadAsync_ShowsProgressAndPrioritizesInSpecMostRecentRows`.
   - Manual sign-off required: confirm operator acceptance of progress UX wording and cadence.
5. Exports library
   - Automated: `NonCoreFlowsParityTests.Exports_*`.
   - Manual sign-off required: none currently identified.
6. Customers
   - Automated: `NonCoreFlowsParityTests.Customers_*`.
   - Manual sign-off required: none currently identified.
7. Settings + Sync Issues
   - Automated: `NonCoreFlowsParityTests.Settings_*`, `NonCoreFlowsParityTests.SettingsAndSyncIssues_ManualTriggerAndRetryDiscard_MaintainParityFlow`.
   - Manual sign-off required: none currently identified.

## Manual Sign-Off Runbook
1. Execute `docs/csharp-manual-signoff-uat.md` against the release-candidate commit.
2. Record tester/date/result for `MS-001`, `MS-002`, and `MS-003`.
3. Treat any failed case as parity blocker until fixed and re-run.

## Acceptance Criteria to Close Remaining Parity
1. Every P0 and P1 item has passing automated evidence or approved manual sign-off.
2. No open critical parity defects for Builder/History/Spreadsheet flows.
3. `docs/csharp-parity-golden-matrix.md` and this checklist are both up to date in the same commit.

## Deferred to Release Hardening (Not Parity Scope)
1. Signing/notarization secret provisioning and activation.
2. `csharp-release-stubs` dispatch once workflow exists on default branch.
3. Final release cutover and rollback rehearsals.
