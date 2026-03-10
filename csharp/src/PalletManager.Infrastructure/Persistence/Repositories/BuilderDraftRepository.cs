using System.Text.Json;
using PalletManager.Application.Contracts;
using PalletManager.Domain.Entities;
using PalletManager.Infrastructure.Persistence;

namespace PalletManager.Infrastructure.Persistence.Repositories;

public sealed class BuilderDraftRepository : IBuilderDraftRepository
{
    private readonly SqliteConnectionFactory _factory;
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);

    public BuilderDraftRepository(SqliteConnectionFactory factory)
    {
        _factory = factory;
    }

    public async Task<BuilderDraft?> GetAsync(CancellationToken ct = default)
    {
        await using var connection = await _factory.OpenAsync(ct);
        await using var cmd = connection.CreateCommand();
        cmd.CommandText = @"
SELECT pallet_json, fallback_serials_json, selected_customer_id, template_type, pallet_size, packout_date, pallet_number_draft
FROM builder_draft
WHERE id = 1;";

        await using var reader = await cmd.ExecuteReaderAsync(ct);
        if (!await reader.ReadAsync(ct))
        {
            return null;
        }

        var palletJson = reader.IsDBNull(0) ? null : reader.GetString(0);
        var fallbackJson = reader.IsDBNull(1) ? "[]" : reader.GetString(1);

        return new BuilderDraft
        {
            ActivePallet = string.IsNullOrWhiteSpace(palletJson)
                ? null
                : JsonSerializer.Deserialize<Pallet>(palletJson, JsonOptions),
            FallbackSerials = JsonSerializer.Deserialize<List<string>>(fallbackJson, JsonOptions) ?? new List<string>(),
            SelectedCustomerId = reader.IsDBNull(2) ? null : reader.GetInt32(2),
            TemplateType = reader.GetString(3),
            PalletSize = reader.GetInt32(4),
            PackoutDate = DateOnly.Parse(reader.GetString(5)),
            PalletNumberDraft = reader.IsDBNull(6) ? null : reader.GetString(6),
        };
    }

    public async Task SaveAsync(BuilderDraft draft, CancellationToken ct = default)
    {
        var palletJson = draft.ActivePallet is null ? null : JsonSerializer.Serialize(draft.ActivePallet, JsonOptions);
        var fallbackJson = JsonSerializer.Serialize(draft.FallbackSerials, JsonOptions);

        await using var connection = await _factory.OpenAsync(ct);
        await using var cmd = connection.CreateCommand();
        cmd.CommandText = @"
INSERT INTO builder_draft(id, pallet_json, fallback_serials_json, selected_customer_id, template_type, pallet_size, packout_date, pallet_number_draft, updated_at)
VALUES (1, $pallet_json, $fallback_json, $selected_customer_id, $template_type, $pallet_size, $packout_date, $pallet_number_draft, $updated_at)
ON CONFLICT(id) DO UPDATE SET
  pallet_json = excluded.pallet_json,
  fallback_serials_json = excluded.fallback_serials_json,
  selected_customer_id = excluded.selected_customer_id,
  template_type = excluded.template_type,
  pallet_size = excluded.pallet_size,
  packout_date = excluded.packout_date,
  pallet_number_draft = excluded.pallet_number_draft,
  updated_at = excluded.updated_at;";

        cmd.Parameters.AddWithValue("$pallet_json", (object?)palletJson ?? DBNull.Value);
        cmd.Parameters.AddWithValue("$fallback_json", fallbackJson);
        cmd.Parameters.AddWithValue("$selected_customer_id", (object?)draft.SelectedCustomerId ?? DBNull.Value);
        cmd.Parameters.AddWithValue("$template_type", draft.TemplateType);
        cmd.Parameters.AddWithValue("$pallet_size", draft.PalletSize);
        cmd.Parameters.AddWithValue("$packout_date", draft.PackoutDate.ToString("yyyy-MM-dd"));
        cmd.Parameters.AddWithValue("$pallet_number_draft", (object?)draft.PalletNumberDraft ?? DBNull.Value);
        cmd.Parameters.AddWithValue("$updated_at", DateTime.UtcNow.ToString("O"));

        await cmd.ExecuteNonQueryAsync(ct);
    }

    public async Task ClearAsync(CancellationToken ct = default)
    {
        await using var connection = await _factory.OpenAsync(ct);
        await using var cmd = connection.CreateCommand();
        cmd.CommandText = "DELETE FROM builder_draft WHERE id = 1;";
        await cmd.ExecuteNonQueryAsync(ct);
    }
}
