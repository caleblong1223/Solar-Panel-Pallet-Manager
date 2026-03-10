using System.Text.Json;
using PalletManager.Application.Contracts;
using PalletManager.Domain.Entities;
using PalletManager.Infrastructure.Persistence;

namespace PalletManager.Infrastructure.Persistence.Repositories;

public sealed class LocalCacheRepository : ILocalCacheRepository
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);
    private readonly SqliteConnectionFactory _factory;

    public LocalCacheRepository(SqliteConnectionFactory factory)
    {
        _factory = factory;
    }

    public async Task UpsertCustomersAsync(IEnumerable<Customer> customers, CancellationToken ct = default)
    {
        await using var connection = await _factory.OpenAsync(ct);
        await using var tx = await connection.BeginTransactionAsync(ct);
        foreach (var customer in customers)
        {
            await using var cmd = connection.CreateCommand();
            cmd.Transaction = (Microsoft.Data.Sqlite.SqliteTransaction)tx;
            cmd.CommandText = @"
INSERT INTO cached_customers(id, display_name, contact_name, business_name, email, phone, address, city, state, zip_code, is_active, created_at, updated_at)
VALUES ($id, $display_name, $contact_name, $business_name, $email, $phone, $address, $city, $state, $zip_code, $is_active, $created_at, $updated_at)
ON CONFLICT(id) DO UPDATE SET
  display_name = excluded.display_name,
  contact_name = excluded.contact_name,
  business_name = excluded.business_name,
  email = excluded.email,
  phone = excluded.phone,
  address = excluded.address,
  city = excluded.city,
  state = excluded.state,
  zip_code = excluded.zip_code,
  is_active = excluded.is_active,
  updated_at = excluded.updated_at;";
            cmd.Parameters.AddWithValue("$id", customer.Id);
            cmd.Parameters.AddWithValue("$display_name", customer.DisplayName);
            cmd.Parameters.AddWithValue("$contact_name", (object?)customer.ContactName ?? DBNull.Value);
            cmd.Parameters.AddWithValue("$business_name", (object?)customer.BusinessName ?? DBNull.Value);
            cmd.Parameters.AddWithValue("$email", (object?)customer.Email ?? DBNull.Value);
            cmd.Parameters.AddWithValue("$phone", (object?)customer.Phone ?? DBNull.Value);
            cmd.Parameters.AddWithValue("$address", (object?)customer.Address ?? DBNull.Value);
            cmd.Parameters.AddWithValue("$city", (object?)customer.City ?? DBNull.Value);
            cmd.Parameters.AddWithValue("$state", (object?)customer.State ?? DBNull.Value);
            cmd.Parameters.AddWithValue("$zip_code", (object?)customer.ZipCode ?? DBNull.Value);
            cmd.Parameters.AddWithValue("$is_active", customer.IsActive ? 1 : 0);
            cmd.Parameters.AddWithValue("$created_at", customer.CreatedAtUtc?.ToString("O") ?? (object)DBNull.Value);
            cmd.Parameters.AddWithValue("$updated_at", DateTime.UtcNow.ToString("O"));
            await cmd.ExecuteNonQueryAsync(ct);
        }

        await tx.CommitAsync(ct);
    }

    public async Task<IReadOnlyList<Customer>> GetCustomersAsync(bool includeInactive, string? search, CancellationToken ct = default)
    {
        var rows = new List<Customer>();
        await using var connection = await _factory.OpenAsync(ct);
        await using var cmd = connection.CreateCommand();
        cmd.CommandText = @"
SELECT id, display_name, contact_name, business_name, email, phone, address, city, state, zip_code, is_active, created_at
FROM cached_customers
WHERE ($include_inactive = 1 OR is_active = 1)
  AND ($search = '' OR display_name LIKE '%' || $search || '%')
ORDER BY display_name ASC;";
        cmd.Parameters.AddWithValue("$include_inactive", includeInactive ? 1 : 0);
        cmd.Parameters.AddWithValue("$search", search?.Trim() ?? string.Empty);

        await using var reader = await cmd.ExecuteReaderAsync(ct);
        while (await reader.ReadAsync(ct))
        {
            rows.Add(new Customer
            {
                Id = reader.GetInt32(0),
                DisplayName = reader.GetString(1),
                ContactName = reader.IsDBNull(2) ? null : reader.GetString(2),
                BusinessName = reader.IsDBNull(3) ? null : reader.GetString(3),
                Email = reader.IsDBNull(4) ? null : reader.GetString(4),
                Phone = reader.IsDBNull(5) ? null : reader.GetString(5),
                Address = reader.IsDBNull(6) ? null : reader.GetString(6),
                City = reader.IsDBNull(7) ? null : reader.GetString(7),
                State = reader.IsDBNull(8) ? null : reader.GetString(8),
                ZipCode = reader.IsDBNull(9) ? null : reader.GetString(9),
                IsActive = reader.GetInt64(10) == 1,
                CreatedAtUtc = reader.IsDBNull(11) ? null : DateTime.Parse(reader.GetString(11)),
            });
        }

        return rows;
    }

    public async Task UpsertPalletAsync(Pallet pallet, CancellationToken ct = default)
    {
        var json = JsonSerializer.Serialize(pallet, JsonOptions);
        await using var connection = await _factory.OpenAsync(ct);
        await using var cmd = connection.CreateCommand();
        cmd.CommandText = @"
INSERT INTO cached_pallets(id, status, pallet_number, template_type, max_panels, customer_id, created_at, completed_at, deleted_at, item_count, pallet_json, updated_at)
VALUES ($id, $status, $pallet_number, $template_type, $max_panels, $customer_id, $created_at, $completed_at, $deleted_at, $item_count, $pallet_json, $updated_at)
ON CONFLICT(id) DO UPDATE SET
  status = excluded.status,
  pallet_number = excluded.pallet_number,
  template_type = excluded.template_type,
  max_panels = excluded.max_panels,
  customer_id = excluded.customer_id,
  completed_at = excluded.completed_at,
  deleted_at = excluded.deleted_at,
  item_count = excluded.item_count,
  pallet_json = excluded.pallet_json,
  updated_at = excluded.updated_at;";
        cmd.Parameters.AddWithValue("$id", pallet.Id);
        cmd.Parameters.AddWithValue("$status", pallet.Status);
        cmd.Parameters.AddWithValue("$pallet_number", pallet.PalletNumber);
        cmd.Parameters.AddWithValue("$template_type", (object?)pallet.TemplateType ?? DBNull.Value);
        cmd.Parameters.AddWithValue("$max_panels", pallet.MaxPanels);
        cmd.Parameters.AddWithValue("$customer_id", (object?)pallet.CustomerId ?? DBNull.Value);
        cmd.Parameters.AddWithValue("$created_at", pallet.CreatedAtUtc.ToString("O"));
        cmd.Parameters.AddWithValue("$completed_at", pallet.CompletedAtUtc?.ToString("O") ?? (object)DBNull.Value);
        cmd.Parameters.AddWithValue("$deleted_at", pallet.DeletedAtUtc?.ToString("O") ?? (object)DBNull.Value);
        cmd.Parameters.AddWithValue("$item_count", pallet.ItemCount);
        cmd.Parameters.AddWithValue("$pallet_json", json);
        cmd.Parameters.AddWithValue("$updated_at", DateTime.UtcNow.ToString("O"));
        await cmd.ExecuteNonQueryAsync(ct);
    }

    public async Task<IReadOnlyList<Pallet>> GetPalletsAsync(string status, CancellationToken ct = default)
    {
        var rows = new List<Pallet>();
        await using var connection = await _factory.OpenAsync(ct);
        await using var cmd = connection.CreateCommand();
        cmd.CommandText = @"
SELECT pallet_json
FROM cached_pallets
WHERE status = $status
ORDER BY COALESCE(completed_at, created_at) DESC;";
        cmd.Parameters.AddWithValue("$status", status);

        await using var reader = await cmd.ExecuteReaderAsync(ct);
        while (await reader.ReadAsync(ct))
        {
            var json = reader.GetString(0);
            var pallet = JsonSerializer.Deserialize<Pallet>(json, JsonOptions);
            if (pallet is not null)
            {
                rows.Add(pallet);
            }
        }

        return rows;
    }

    public async Task UpsertExportsAsync(IEnumerable<ExportRecord> exports, CancellationToken ct = default)
    {
        await using var connection = await _factory.OpenAsync(ct);
        await using var tx = await connection.BeginTransactionAsync(ct);
        foreach (var row in exports)
        {
            await using var cmd = connection.CreateCommand();
            cmd.Transaction = (Microsoft.Data.Sqlite.SqliteTransaction)tx;
            cmd.CommandText = @"
INSERT INTO cached_exports(id, pallet_id, template_type, packout_date, file_name, mime_type, size_bytes, object_key, checksum_sha256, created_at, updated_at)
VALUES ($id, $pallet_id, $template_type, $packout_date, $file_name, $mime_type, $size_bytes, $object_key, $checksum, $created_at, $updated_at)
ON CONFLICT(id) DO UPDATE SET
  pallet_id = excluded.pallet_id,
  template_type = excluded.template_type,
  packout_date = excluded.packout_date,
  file_name = excluded.file_name,
  mime_type = excluded.mime_type,
  size_bytes = excluded.size_bytes,
  object_key = excluded.object_key,
  checksum_sha256 = excluded.checksum_sha256,
  created_at = excluded.created_at,
  updated_at = excluded.updated_at;";
            cmd.Parameters.AddWithValue("$id", row.Id);
            cmd.Parameters.AddWithValue("$pallet_id", row.PalletId);
            cmd.Parameters.AddWithValue("$template_type", row.TemplateType);
            cmd.Parameters.AddWithValue("$packout_date", row.PackoutDate?.ToString("yyyy-MM-dd") ?? (object)DBNull.Value);
            cmd.Parameters.AddWithValue("$file_name", row.FileName);
            cmd.Parameters.AddWithValue("$mime_type", row.MimeType);
            cmd.Parameters.AddWithValue("$size_bytes", (object?)row.SizeBytes ?? DBNull.Value);
            cmd.Parameters.AddWithValue("$object_key", row.ObjectKey);
            cmd.Parameters.AddWithValue("$checksum", (object?)row.ChecksumSha256 ?? DBNull.Value);
            cmd.Parameters.AddWithValue("$created_at", row.CreatedAtUtc.ToString("O"));
            cmd.Parameters.AddWithValue("$updated_at", DateTime.UtcNow.ToString("O"));
            await cmd.ExecuteNonQueryAsync(ct);
        }

        await tx.CommitAsync(ct);
    }

    public async Task<IReadOnlyList<ExportRecord>> GetExportsByPalletAsync(int palletId, CancellationToken ct = default)
    {
        var rows = new List<ExportRecord>();
        await using var connection = await _factory.OpenAsync(ct);
        await using var cmd = connection.CreateCommand();
        cmd.CommandText = @"
SELECT id, pallet_id, template_type, packout_date, object_key, file_name, mime_type, size_bytes, checksum_sha256, created_at
FROM cached_exports
WHERE pallet_id = $pallet_id
ORDER BY created_at DESC;";
        cmd.Parameters.AddWithValue("$pallet_id", palletId);

        await using var reader = await cmd.ExecuteReaderAsync(ct);
        while (await reader.ReadAsync(ct))
        {
            rows.Add(new ExportRecord
            {
                Id = reader.GetInt32(0),
                PalletId = reader.GetInt32(1),
                TemplateType = reader.GetString(2),
                PackoutDate = reader.IsDBNull(3) ? null : DateOnly.Parse(reader.GetString(3)),
                ObjectKey = reader.GetString(4),
                FileName = reader.GetString(5),
                MimeType = reader.GetString(6),
                SizeBytes = reader.IsDBNull(7) ? null : reader.GetInt64(7),
                ChecksumSha256 = reader.IsDBNull(8) ? null : reader.GetString(8),
                CreatedAtUtc = DateTime.Parse(reader.GetString(9)),
            });
        }

        return rows;
    }
}
