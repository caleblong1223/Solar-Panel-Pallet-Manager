# PalletManager.IntegrationTests

Integration tests exercising real infrastructure components together (SQLite + repositories + sync engine).

Current scenarios:
- Outbox replay success removes persisted operations
- 409/422 conflict replay transitions persisted operations to needs_review
- SyncIssues retry flow clears needs_review and replays successfully
