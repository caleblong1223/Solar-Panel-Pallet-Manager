PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
  version INTEGER PRIMARY KEY,
  applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runtime_settings (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  primary_api_base_url TEXT NOT NULL,
  fallback_api_base_url TEXT,
  lock_to_local_backend INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS auth_session (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  access_token TEXT,
  user_json TEXT,
  session_mode TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_state (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  syncing INTEGER NOT NULL DEFAULT 0,
  last_sync_at TEXT,
  pending_count INTEGER NOT NULL DEFAULT 0,
  failed_count INTEGER NOT NULL DEFAULT 0,
  needs_review_count INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outbox_operations (
  op_id TEXT PRIMARY KEY,
  op_type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  state TEXT NOT NULL,
  attempt_count INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  last_error_code TEXT,
  next_retry_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS id_mappings (
  entity_type TEXT NOT NULL,
  local_id INTEGER NOT NULL,
  remote_id INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (entity_type, local_id)
);

CREATE TABLE IF NOT EXISTS builder_draft (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  pallet_json TEXT,
  fallback_serials_json TEXT,
  selected_customer_id INTEGER,
  template_type TEXT NOT NULL,
  pallet_size INTEGER NOT NULL,
  packout_date TEXT NOT NULL,
  pallet_number_draft TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cached_customers (
  id INTEGER PRIMARY KEY,
  display_name TEXT NOT NULL,
  contact_name TEXT,
  business_name TEXT,
  email TEXT,
  phone TEXT,
  address TEXT,
  city TEXT,
  state TEXT,
  zip_code TEXT,
  is_active INTEGER NOT NULL,
  created_at TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cached_pallets (
  id INTEGER PRIMARY KEY,
  status TEXT NOT NULL,
  pallet_number INTEGER NOT NULL,
  template_type TEXT,
  max_panels INTEGER NOT NULL,
  customer_id INTEGER,
  created_at TEXT NOT NULL,
  completed_at TEXT,
  deleted_at TEXT,
  item_count INTEGER NOT NULL,
  pallet_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cached_exports (
  id INTEGER PRIMARY KEY,
  pallet_id INTEGER NOT NULL,
  template_type TEXT NOT NULL,
  packout_date TEXT,
  file_name TEXT NOT NULL,
  mime_type TEXT NOT NULL,
  size_bytes INTEGER,
  object_key TEXT NOT NULL,
  checksum_sha256 TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
