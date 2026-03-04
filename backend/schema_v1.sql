-- Generated baseline schema for Pallet Manager 2.0
-- Canonical source is Alembic migrations:
--   20260303_0001_initial_schema.py
--   20260303_0002_schema_indexes_and_trgm.py

-- Use: psql -d pallet_manager -f schema_v1.sql

-- Enable pg_trgm extension for trigram indexes used in search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS roles (
  id BIGSERIAL PRIMARY KEY,
  name VARCHAR(64) NOT NULL UNIQUE,
  description VARCHAR(255),
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
  id BIGSERIAL PRIMARY KEY,
  username VARCHAR(100) NOT NULL UNIQUE,
  email VARCHAR(255) UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_roles (
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role_id BIGINT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  PRIMARY KEY (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS customers (
  id BIGSERIAL PRIMARY KEY,
  display_name VARCHAR(255) NOT NULL UNIQUE,
  contact_name VARCHAR(255),
  business_name VARCHAR(255),
  email VARCHAR(255),
  phone VARCHAR(100),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pallets (
  id BIGSERIAL PRIMARY KEY,
  pallet_number INTEGER NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  template_type VARCHAR(32),
  max_panels INTEGER NOT NULL DEFAULT 25,
  customer_id BIGINT REFERENCES customers(id) ON DELETE SET NULL,
  created_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
  completed_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at TIMESTAMPTZ,
  deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS pallet_items (
  id BIGSERIAL PRIMARY KEY,
  pallet_id BIGINT NOT NULL REFERENCES pallets(id) ON DELETE CASCADE,
  serial VARCHAR(128) NOT NULL,
  slot_index INTEGER NOT NULL,
  added_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
  added_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_pallet_items_pallet_serial UNIQUE (pallet_id, serial),
  CONSTRAINT uq_pallet_items_pallet_slot UNIQUE (pallet_id, slot_index)
);

CREATE TABLE IF NOT EXISTS sim_import_batches (
  id BIGSERIAL PRIMARY KEY,
  source_filename VARCHAR(512) NOT NULL,
  source_object_key VARCHAR(1024),
  source_checksum VARCHAR(128),
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  rows_total INTEGER,
  rows_imported INTEGER,
  rows_rejected INTEGER,
  error_summary TEXT,
  imported_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS sim_panels (
  id BIGSERIAL PRIMARY KEY,
  batch_id BIGINT NOT NULL REFERENCES sim_import_batches(id) ON DELETE CASCADE,
  serial VARCHAR(128) NOT NULL,
  test_timestamp TIMESTAMPTZ,
  panel_type VARCHAR(64),
  watts NUMERIC(10,2),
  voc NUMERIC(10,3),
  isc NUMERIC(10,3),
  vmp NUMERIC(10,3),
  imp NUMERIC(10,3),
  ff NUMERIC(10,3),
  result VARCHAR(32),
  raw_payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_sim_panels_serial_test_ts UNIQUE (serial, test_timestamp)
);

CREATE TABLE IF NOT EXISTS exports (
  id BIGSERIAL PRIMARY KEY,
  pallet_id BIGINT NOT NULL REFERENCES pallets(id) ON DELETE CASCADE,
  template_type VARCHAR(64) NOT NULL,
  object_key VARCHAR(1024) NOT NULL,
  file_name VARCHAR(255) NOT NULL,
  mime_type VARCHAR(100) NOT NULL DEFAULT 'application/pdf',
  size_bytes BIGINT,
  checksum_sha256 VARCHAR(128),
  created_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_events (
  id BIGSERIAL PRIMARY KEY,
  actor_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
  event_type VARCHAR(100) NOT NULL,
  resource_type VARCHAR(100) NOT NULL,
  resource_id VARCHAR(100),
  outcome VARCHAR(32) NOT NULL,
  message TEXT,
  metadata_json JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_pallet_items_serial ON pallet_items(serial);
CREATE INDEX IF NOT EXISTS ix_pallets_completed_at ON pallets(completed_at);
CREATE INDEX IF NOT EXISTS ix_pallets_status ON pallets(status);
CREATE INDEX IF NOT EXISTS ix_pallets_customer_id ON pallets(customer_id);
CREATE INDEX IF NOT EXISTS ix_pallets_pallet_number ON pallets(pallet_number);
CREATE INDEX IF NOT EXISTS ix_pallets_customer_status_completed
  ON pallets(customer_id, status, completed_at);
CREATE INDEX IF NOT EXISTS ix_pallets_completed_by ON pallets(completed_by);

CREATE INDEX IF NOT EXISTS ix_sim_import_batches_status_created_at
  ON sim_import_batches(status, created_at);
CREATE INDEX IF NOT EXISTS ix_sim_import_batches_imported_by
  ON sim_import_batches(imported_by);

CREATE INDEX IF NOT EXISTS ix_sim_panels_serial ON sim_panels(serial);
CREATE INDEX IF NOT EXISTS ix_sim_panels_batch_id ON sim_panels(batch_id);

CREATE INDEX IF NOT EXISTS ix_exports_pallet_id ON exports(pallet_id);
CREATE INDEX IF NOT EXISTS ix_exports_created_at ON exports(created_at);
CREATE INDEX IF NOT EXISTS ix_exports_pallet_id_created_at
  ON exports(pallet_id, created_at);

CREATE INDEX IF NOT EXISTS ix_audit_events_created_at ON audit_events(created_at);
CREATE INDEX IF NOT EXISTS ix_audit_events_resource
  ON audit_events(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS ix_audit_events_actor_created_at
  ON audit_events(actor_user_id, created_at);
CREATE INDEX IF NOT EXISTS ix_audit_events_event_type
  ON audit_events(event_type);

-- Trigram indexes for partial search
CREATE INDEX IF NOT EXISTS ix_pallet_items_serial_trgm
  ON pallet_items
  USING gin (serial gin_trgm_ops);

CREATE INDEX IF NOT EXISTS ix_sim_panels_serial_trgm
  ON sim_panels
  USING gin (serial gin_trgm_ops);

CREATE INDEX IF NOT EXISTS ix_customers_display_name_trgm
  ON customers
  USING gin (display_name gin_trgm_ops);
