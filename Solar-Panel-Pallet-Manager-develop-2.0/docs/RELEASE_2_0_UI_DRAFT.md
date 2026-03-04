# Pallet Manager 2.0 - Modern UI Release Draft

**Status:** Draft  
**Target Version:** 2.0.0  
**Focus:** Full visual modernization using `customtkinter`  
**Current Baseline:** 1.1.0 (`tkinter` + `ttk`)

## Release Summary

Pallet Manager 2.0 introduces a fully modernized desktop interface built on `customtkinter`, while preserving the proven pallet workflow operators already use today.  
This release upgrades look and feel, readability, and interaction flow across the main builder and history screens without changing your core data model or pallet logic.

## What Is New in 2.0

### 1. Modern App Shell and Theming
- Migrated UI layer from classic `tkinter` widgets to `customtkinter` components.
- Added centralized theme system with:
  - Light mode and dark mode support
  - Consistent color tokens for primary, warning, destructive, and status states
  - Standardized spacing, corner radius, and font scale
- Updated typography and control sizing for modern high-resolution displays.

### 2. Rebuilt Main Builder Screen
- New card-based layout for scan workflow and current pallet state.
- Larger, clearer scan entry and status feedback for production-floor visibility.
- Slot visualization updated with stronger hierarchy (filled, empty, warning states).
- Primary actions (Export, Reset, History, Customer) grouped and visually prioritized.

### 3. Rebuilt History Experience
- Modern filter bar for date range, customer, and barcode search.
- Styled table container and details panel for clearer pallet inspection.
- Updated multi-select actions with stronger affordances for print/export workflows.
- Improved visual states for selected rows, hover, and destructive actions.

### 4. Better Feedback and Workflow Clarity
- Standardized toast/modal messaging for success, warning, and error events.
- Progress overlays for long-running operations (history load, file operations, exports).
- Cleaner empty states and first-use states so users always know what to do next.

### 5. Platform-Ready UI Foundations
- UI framework prepared for current modern hardware and OS visuals.
- Better baseline for future enhancements:
  - Role-based views
  - Touch-friendly mode
  - Guided onboarding and in-app help

## What Did Not Change

- Core pallet logic in `PalletManager` remains intact.
- Existing history JSON structure remains compatible.
- Existing export/import workflows remain compatible.
- Existing directory structure and stored files remain compatible.

## Dependency Update

- Added: `customtkinter`
- Kept: existing backend/business logic dependencies
- Notes:
  - Packaging scripts should include `customtkinter` in bundled dependencies.
  - Theme assets should be bundled with app resources.

## Migration Notes (1.1.0 -> 2.0.0)

- No data migration required for current `pallet_history.json`.
- Existing users can install 2.0 over 1.1.0.
- First launch in 2.0 will initialize UI preferences (appearance mode, scaling) with sane defaults.

## Suggested Changelog Entry (Short Form)

## [2.0.0] - 2026-03-03
### Added
- Modernized desktop UI powered by `customtkinter`.
- New theming system with light/dark modes and standardized visual tokens.
- Rebuilt main pallet builder and history screens with modern layout and controls.

### Changed
- Upgraded user interaction patterns for scanning, filtering, table selection, and action feedback.
- Improved visual hierarchy and readability across all primary workflows.

### Compatibility
- Backward-compatible with existing pallet history and file structure.

## Internal Implementation Scope (Engineering)

1. Create `app/ui/theme.py` for shared colors, spacing, fonts, and appearance mode.
2. Build `PalletBuilderGUIv2` using `customtkinter` (`CTk`, `CTkFrame`, `CTkButton`, `CTkEntry`, `CTkLabel`, `CTkOptionMenu`).
3. Build `PalletHistoryWindowV2` with modern filter/action layout and styled table container.
4. Keep business services (`PalletManager`, exporter, importers, archive manager) unchanged behind UI adapters.
5. Update packaging/test scripts to include and validate `customtkinter`.
6. Add smoke tests for startup, scan flow, history load, export, and delete/reset actions.

## Release Announcement Copy (User-Facing)

Pallet Manager 2.0 is here.  
This update delivers a completely refreshed interface designed for modern systems, with improved readability, cleaner workflows, and a faster-feeling experience across pallet building and history management.  
Your existing data and exports remain compatible, so your team can upgrade without workflow disruption.
