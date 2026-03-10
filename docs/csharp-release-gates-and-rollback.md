# C# Release Gates and Rollback Checklist

## Scope
This checklist governs C# desktop releases on `develop/2.0-csharp` before promotion.

## Release Gates
1. `bash csharp/scripts/ci-gate.sh` passes (integration, unit, parity).
2. Packaging smoke passes for `linux-x64`, `osx-arm64`, `win-x64`.
3. Installer smoke passes for `linux-x64`, `osx-arm64`, `win-x64`.
4. Published artifacts include:
   - app host executable
   - `Persistence/Migrations/001_init.sql`
   - `Persistence/Migrations/002_indexes.sql`
   - installer archive (`.tar.gz` or `.zip` depending on platform)
5. Parity evidence is current:
   - `docs/csharp-parity-golden-matrix.md` matches tests.
6. Signing/notarization stub run completed:
   - `.github/workflows/csharp-release-stubs.yml` executed.
   - Signing executes where tools/secrets are present; missing prerequisites are explicitly reported.
7. Manual parity sign-off recorded:
   - `docs/csharp-manual-signoff-record.md` completed for `MS-001`, `MS-002`, and `MS-003`.

## Pre-Release Operator Verification
1. Launch app build and confirm blue shell loads.
2. Validate Builder start/add/remove/complete workflow.
3. Validate History filter and merge export flow.
4. Validate spreadsheet edit/save/open flow.
5. Validate offline queue by disconnecting network and replay on reconnect.
6. Validate Settings endpoint probe behavior does not persist temporary values after failed tests.

## Deployment Sequence
1. Merge release candidate to `develop/2.0-csharp`.
2. Run CI gates and packaging smoke matrix.
3. Publish artifacts to release staging.
4. Execute installer smoke and branch smoke install on each target OS.
5. Roll out to pilot users.
6. Promote to broad release after pilot sign-off.

## CI Trigger Notes
1. `csharp-release-stubs.yml` can be dispatched with `gh workflow run` only after the workflow file exists on the remote default branch.
2. Before that point, validate runner behavior by pushing `develop/2.0-csharp` and using push-triggered `CI` workflow results.

## Rollback Triggers
1. Critical parity regression in Builder or History.
2. Data loss/corruption risk in spreadsheet editing.
3. Persistent sync replay failure or conflict explosion.
4. Release artifact cannot launch on supported target OS.

## Rollback Procedure
1. Halt rollout immediately.
2. Repoint users to last known stable JS/Tauri build from `develop/2.0` distribution channel.
3. Preserve failing C# logs, local DB sample, and repro steps.
4. Open regression ticket tagged `csharp-release-blocker`.
5. Patch on `develop/2.0-csharp`, rerun full gate, and restart pilot.

## Evidence to Attach to Release Record
1. CI run URL for `CI` workflow showing `csharp-gate` and `csharp-packaging-smoke`.
2. CI run URL for `C# Release Stubs` workflow.
3. Command output excerpt for:
   - `bash csharp/scripts/ci-gate.sh`
   - `bash csharp/scripts/package-smoke.sh <rid>`
   - `bash csharp/scripts/installer-smoke.sh <rid>`
4. Parity matrix revision link and commit hash.
