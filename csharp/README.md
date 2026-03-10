# Pallet Manager C# Workspace

This workspace contains the C# cross-platform desktop scaffold for the Pallet Manager 2.0 UI rewrite.

## Goals
- Cross-platform desktop UI (Windows/macOS/Linux)
- Functional parity with the existing React/Tauri frontend
- Offline-first operation with reliable sync replay
- Keep existing Python backend APIs for parity and delivery speed

## Structure
- `src/PalletManager.Domain`: core models/enums/errors
- `src/PalletManager.Application`: contracts and use-case orchestration
- `src/PalletManager.Infrastructure`: API/persistence/sync/platform services
- `src/PalletManager.Desktop.Avalonia`: UI layer (Avalonia + MVVM)
- `tests`: unit, integration, and parity test projects

## Gate Command
Run the C# parity gate locally:

```bash
bash csharp/scripts/ci-gate.sh
```

This command executes integration, unit, and parity suites in order.

## Packaging Smoke
Run a cross-platform publish smoke check for a target runtime identifier:

```bash
bash csharp/scripts/package-smoke.sh osx-arm64
```

Common runtime identifiers:
- `linux-x64`
- `osx-arm64`
- `win-x64`

This script validates:
- publish output generation
- app host artifact existence
- embedded SQLite migration assets (`001_init.sql`, `002_indexes.sql`)
- non-interactive launch/open/close smoke (`--smoke`) when host OS matches RID

## Installer Smoke
Generate installer-style artifacts and validate install/uninstall behavior:

```bash
bash csharp/scripts/installer-smoke.sh osx-arm64
```

This script validates:
- installer artifact generation (`.tar.gz` on macOS/Linux, `.zip` on Windows)
- extract/install flow
- launch/open/close smoke from installed location
- uninstall cleanup

## Signing Stub
Run signing/notarization stub checks against generated artifacts:

```bash
bash csharp/scripts/signing-stub.sh osx-arm64 csharp/artifacts/installers/osx-arm64 csharp/artifacts/publish/osx-arm64
```

This script:
- verifies artifact folder presence
- signs binaries/artifacts when platform tools and secrets are present
- safely skips signing/notarization paths when prerequisites are missing

## Provision Release Secrets
Populate GitHub Actions secrets used by `csharp-release-stubs`:

```bash
bash csharp/scripts/provision-release-secrets.sh
```

Optional environment inputs:
- `APPLE_SIGNING_IDENTITY`
- `APPLE_TEAM_ID`
- `APPLE_NOTARY_PROFILE`
- `WINDOWS_CERT_BASE64` or `WINDOWS_CERT_PFX_FILE`
- `WINDOWS_CERT_PASSWORD`
- `LINUX_GPG_PRIVATE_KEY` or `LINUX_GPG_PRIVATE_KEY_FILE`

## Parity Evidence
- Golden scenario matrix: `docs/csharp-parity-golden-matrix.md`
- Parity test project notes: `csharp/tests/PalletManager.ParityTests/README.md`
- Release gates and rollback checklist: `docs/csharp-release-gates-and-rollback.md`

## Next Actions
1. Expand parity fixtures to include additional production export workbook variants
2. Provision CI secrets and certificates to activate real signing/notarization in `csharp-release-stubs`
3. Validate installer and signing flows on all target OS runners
4. Continue branch-level parity comparison against JS/Tauri snapshots
