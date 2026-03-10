# Taskmaster Backlog - C# UI Parity Program

Source docs:
- `docs/csharp-ui-parity-roadmap.md`
- `docs/PRD_PALLET_MANAGER_2_0.md`
- `docs/TDD_PALLET_MANAGER_2_0.md`

Tag: `csharp-ui`

## Milestone A - Foundation

### CSPM-001
- Title: Create .NET 8 solution and project wiring
- Dependencies: None
- Acceptance criteria:
  - Domain/Application/Infrastructure/Desktop projects compile references
  - Avalonia startup pipeline is wired

### CSPM-002
- Title: Implement DI composition root and baseline services
- Dependencies: CSPM-001
- Acceptance criteria:
  - All application contracts resolve from DI
  - Desktop app can launch shell without runtime DI failures

### CSPM-003
- Title: Implement blue identity theme system
- Dependencies: CSPM-001
- Acceptance criteria:
  - Tokenized blue palette is applied app-wide
  - Shell and controls follow flat visual style

## Milestone B - Data and Connectivity

### CSPM-010
- Title: Implement SQLite migration runner and repository base
- Dependencies: CSPM-002
- Acceptance criteria:
  - `001_init.sql` and `002_indexes.sql` are applied automatically
  - DB file is created and WAL enabled

### CSPM-011
- Title: Implement runtime settings persistence and endpoint resolver
- Dependencies: CSPM-010
- Acceptance criteria:
  - Primary/fallback/local/docker-host candidate ordering works
  - Settings persist and reload across restarts

### CSPM-012
- Title: Implement HTTP client fallback policy parity
- Dependencies: CSPM-011
- Acceptance criteria:
  - timeout/network/5xx fallback to next endpoint
  - 4xx errors return immediately with mapped API error

## Milestone C - Offline and Sync

### CSPM-020
- Title: Implement outbox repository in SQLite
- Dependencies: CSPM-010
- Acceptance criteria:
  - pending/needs_review states persisted
  - retry metadata persisted

### CSPM-021
- Title: Implement sync engine replay loop parity
- Dependencies: CSPM-020, CSPM-012
- Acceptance criteria:
  - replay flow supports pallet.create/item_add/item_remove/complete
  - conflict routing to needs_review matches JS behavior

### CSPM-022
- Title: Implement sync issues workflow parity
- Dependencies: CSPM-021
- Acceptance criteria:
  - retry/discard actions operate on durable outbox records
  - global sync counters update shell/status page

## Milestone D - High-Risk UI Parity

### CSPM-030
- Title: Implement Builder screen parity
- Dependencies: CSPM-011, CSPM-021
- Acceptance criteria:
  - active draft persistence
  - missing simulator modal flow parity
  - complete/export flow parity

### CSPM-031
- Title: Implement History Explorer parity
- Dependencies: CSPM-030
- Acceptance criteria:
  - filter/query/sort parity
  - single select details and multi-select merge parity

### CSPM-032
- Title: Implement Spreadsheet editor parity spike + production path
- Dependencies: CSPM-031
- Acceptance criteria:
  - load/edit/save workbook path works against backend
  - performance validated with representative workbooks

## Milestone E - Remaining Screens and Release

### CSPM-040
- Title: Implement Customers, Import, Exports, Settings parity
- Dependencies: CSPM-030
- Acceptance criteria:
  - all screens mapped with parity behavior
  - offline cache fallbacks available where required

### CSPM-041
- Title: Build parity test harness and golden scenarios
- Dependencies: CSPM-032, CSPM-040
- Acceptance criteria:
  - automated parity coverage for core operator workflows
  - no critical behavior regression vs JS build

### CSPM-042
- Title: Cross-platform packaging and release gates
- Dependencies: CSPM-041
- Acceptance criteria:
  - signed/releasable artifacts for Windows/macOS/Linux
  - go-live checklist and rollback plan documented
