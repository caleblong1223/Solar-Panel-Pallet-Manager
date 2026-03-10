# PalletManager.ParityTests

Parity-focused behavioral tests that validate C# workflows against golden fixtures.

Current coverage:
- CSV golden fixture parsing baseline
- XLSX load/edit/save roundtrip with cell-level equivalence assertions
- Production-like multi-sheet fixture parity (sparse rows + formula preservation contracts)
- Non-core flow parity checks (Customers/Import/Exports/Settings operator-visible behavior)
- Core flow journeys (Builder missing-SIM branches and History refresh/filter/merge/open paths)
