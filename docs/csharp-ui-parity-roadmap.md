# Pallet Manager 2.0 C# Cross-Platform Rewrite

## 1. Objective
Build a new cross-platform C# desktop UI with a blue-forward modern flat visual identity while preserving behavior parity with the current React/Tauri frontend.

## 2. Scope and Non-Goals
- In scope:
  - UI rewrite to Avalonia + MVVM
  - Offline-first behavior with sync replay parity
  - Existing backend API compatibility
  - Cross-platform desktop packaging for Windows/macOS/Linux
- Out of scope (initial program):
  - Python backend rewrite
  - API contract redesign
  - Data model contract changes

## 3. Platform and Stack Decisions
- UI framework: Avalonia (desktop cross-platform)
- Pattern: MVVM + DI + hosted background services
- Local persistence: SQLite (WAL mode)
- Spreadsheet: OpenXML-based service + editable grid UI
- HTTP: typed client with endpoint fallback strategy and operation-id headers

## 4. Visual Identity (New Design System)
- Direction: blue-centric, modern flat, high readability, minimal chrome
- Token model:
  - `bg-0`: `#f3f7fc`
  - `bg-1`: `#e8f0fa`
  - `surface`: `#ffffff`
  - `border`: `#c8d8ea`
  - `text`: `#0f2238`
  - `muted`: `#4c6783`
  - `accent-500`: `#1f6fb2`
  - `accent-600`: `#175a91`

## 5. Repository Layout
- C# scaffold root: `csharp/`
- Domain: `csharp/src/PalletManager.Domain`
- Application: `csharp/src/PalletManager.Application`
- Infrastructure: `csharp/src/PalletManager.Infrastructure`
- Desktop UI: `csharp/src/PalletManager.Desktop.Avalonia`
- Tests: `csharp/tests/`

## 6. Architecture Blueprint

### 6.1 Layered Model
1. Domain
   - Entities, enums, and error contracts
2. Application
   - Interface contracts and use case orchestration
3. Infrastructure
   - API, SQLite repositories, sync engine, platform launchers, spreadsheet service
4. Presentation
   - Avalonia views and view models

### 6.2 API Connectivity Model
Ordered endpoint candidate list:
1. Runtime setting `PrimaryApiBaseUrl`
2. Runtime setting `FallbackApiBaseUrl`
3. `http://127.0.0.1:8000/api/v1`
4. `http://localhost:8000/api/v1`
5. Optional Docker-host helper (`http://host.docker.internal:8000/api/v1` where supported)

Retry/fallback triggers:
- timeout/network failure
- HTTP 5xx

No fallback trigger:
- HTTP 4xx (treat as business/data error)

## 7. Parity-First Behavioral Contract

### 7.1 Global Shell
- Left navigation and top status summary must remain functionally equivalent
- Global toast notifications must be available from all feature workflows

### 7.2 Builder
- Active/inactive pallet modes
- Draft persistence across restarts
- Missing simulator decision modal parity
- Complete pallet workflow parity (create -> add items -> complete -> export)

### 7.3 History
- Same filter semantics (date presets, exact match, sorting)
- Single select details + multi-select merge behavior
- Spreadsheet editor open/edit/save parity

### 7.4 Customers
- Create/edit/archive behavior parity
- Offline cached fallback parity

### 7.5 Sync Issues
- `pending` vs `needs_review` state behavior parity
- Retry/discard action parity
- Guidance text mapping parity

### 7.6 Settings
- Runtime endpoint testing parity
- Live backend health and sync state display parity

## 8. SQLite Schema and Storage Policy
Migrations:
- `csharp/src/PalletManager.Infrastructure/Persistence/Migrations/001_init.sql`
- `csharp/src/PalletManager.Infrastructure/Persistence/Migrations/002_indexes.sql`

Key tables:
- `runtime_settings`
- `sync_state`
- `outbox_operations`
- `id_mappings`
- `builder_draft`
- `cached_customers`
- `cached_pallets`
- `cached_exports`

Storage principles:
- SQLite as source of truth for local/offline state
- API as source of truth for system-of-record data
- queued mutations in outbox with durable retry metadata

## 9. Offline + Docker-Hosted Connectability Plan
- App remains API-driven; direct DB socket access is not required in desktop client
- Python backend (Docker-hosted or local) remains the integration boundary
- If backend is unreachable:
  - reads served from local cache when possible
  - writes enqueue to outbox and replay when connectivity returns
- Sync replay must include operation id for dedupe

## 10. Implementation Roadmap

### Phase 0: Baseline and Freeze
- Freeze existing frontend behavior with parity scenarios
- Capture canonical payloads and expected state transitions

### Phase 1: Foundations
- DI and app composition root
- Runtime settings and endpoint resolver
- HTTP client and error contract mapping
- SQLite migrations + repository plumbing

### Phase 2: Sync Core
- Outbox repository implementation
- Sync engine hosted service with backoff and conflict routing
- Sync state observable for shell/status

### Phase 3: High-Risk UX
- Builder workflow and draft persistence
- History filters/details/exports
- Spreadsheet editor load/edit/save

### Phase 4: Remaining Screens
- Customers
- Import simulator
- Export library
- Settings and Sync Issues full behavior

### Phase 5: Hardening
- Cross-platform packaging
- Parity test suite pass
- Performance and resilience tuning

## 11. Test Strategy

### 11.1 Unit Tests
- Use case behavior
- Backoff and state transitions
- Mapper/validator rules

### 11.2 Integration Tests
- API client fallback behavior
- SQLite repository persistence and migrations
- Sync replay against controlled backend responses

### 11.3 Parity Tests
Golden user flows:
1. Start pallet -> add/remove -> complete
2. Missing sim decision branches
3. History filtering exact/non-exact and date windows
4. Export open and merge
5. Spreadsheet edit save roundtrip
6. Offline mutation queue and replay

## 12. Branching and Delivery Strategy
- Current branch: `develop/2.0` (JS/Tauri track)
- New branch for C# track: `develop/2.0-csharp`
- Keep both tracks active while parity testing is in progress
- Merge policy:
  - backend API compatibility preserved
  - parity suite pass required before promotion

## 13. Backend Rewrite Decision
Recommendation:
- Keep backend in Python for now.
- Reason:
  - fastest path to UI parity
  - avoids simultaneous front-end + back-end rewrite risk
  - preserves tested API behavior and avoids contract drift

Future option:
- evaluate backend rewrite only after C# UI reaches parity and release stability.

## 14. Immediate Next Tasks
1. Wire real project files and add packages (Avalonia, DI, sqlite, OpenXML)
2. Implement `IApiClient`, endpoint resolver, and settings service
3. Implement SQLite repositories + migration runner
4. Stand up sync hosted service and sync state stream
5. Build Builder and History first with parity tests
