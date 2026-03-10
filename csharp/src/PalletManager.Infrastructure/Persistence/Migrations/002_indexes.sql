CREATE INDEX IF NOT EXISTS idx_outbox_state_retry
ON outbox_operations(state, next_retry_at, created_at);

CREATE INDEX IF NOT EXISTS idx_cached_customers_active_name
ON cached_customers(is_active, display_name);

CREATE INDEX IF NOT EXISTS idx_cached_pallets_status_date
ON cached_pallets(status, completed_at, created_at);

CREATE INDEX IF NOT EXISTS idx_cached_exports_pallet_created
ON cached_exports(pallet_id, created_at);
