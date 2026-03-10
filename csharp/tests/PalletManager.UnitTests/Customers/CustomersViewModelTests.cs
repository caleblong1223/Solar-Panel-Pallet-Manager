using System.Text.Json;
using PalletManager.Application.Contracts;
using PalletManager.Desktop.Avalonia.ViewModels;
using PalletManager.Domain.Entities;
using Xunit;

namespace PalletManager.UnitTests.Customers;

public sealed class CustomersViewModelTests
{
    [Fact]
    public async Task RefreshAsync_UsesApiAndCachesCustomers()
    {
        var api = new FakeApiClient();
        var cache = new InMemoryCacheRepository();
        var vm = new CustomersViewModel(api, new FixedAuthService(), cache);

        await vm.RefreshAsync();

        Assert.Single(vm.Customers);
        Assert.Equal("Acme Solar", vm.Customers[0].DisplayName);
        Assert.Single(cache.CachedCustomers);
        Assert.Contains("Loaded 1 customer(s) from API.", vm.StatusMessage);
    }

    [Fact]
    public async Task RefreshAsync_WhenApiFails_UsesCachedCustomers()
    {
        var api = new FakeApiClient { ThrowOnList = true };
        var cache = new InMemoryCacheRepository();
        cache.CachedCustomers.Add(new Customer { Id = 9, DisplayName = "Cached Co", IsActive = true });
        var vm = new CustomersViewModel(api, new FixedAuthService(), cache);

        await vm.RefreshAsync();

        Assert.Single(vm.Customers);
        Assert.Equal("Cached Co", vm.Customers[0].DisplayName);
        Assert.Equal("Using cached customers (offline).", vm.StatusMessage);
    }

    [Fact]
    public async Task SaveAsync_CreateThenEdit_CallsPostAndPatch()
    {
        var api = new FakeApiClient();
        var cache = new InMemoryCacheRepository();
        var vm = new CustomersViewModel(api, new FixedAuthService(), cache);

        vm.DisplayName = "New Name";
        await vm.SaveAsync();
        Assert.Equal(1, api.PostCalls);

        vm.Customers.Clear();
        vm.Customers.Add(new Customer
        {
            Id = 77,
            DisplayName = "Edit Me",
            IsActive = true,
            Email = "old@x.com",
        });
        vm.StartEdit(77);
        vm.DisplayName = "Edited";
        await vm.SaveAsync();

        Assert.Equal(1, api.PatchCalls);
    }

    [Fact]
    public async Task ArchiveAsync_CallsDelete()
    {
        var api = new FakeApiClient();
        var vm = new CustomersViewModel(api, new FixedAuthService(), new InMemoryCacheRepository());

        await vm.ArchiveAsync(42);

        Assert.Equal("/customers/42", api.LastDeletePath);
    }

    private sealed class FakeApiClient : IApiClient
    {
        public bool ThrowOnList { get; set; }
        public int PostCalls { get; private set; }
        public int PatchCalls { get; private set; }
        public string LastDeletePath { get; private set; } = string.Empty;

        public Task<T> GetAsync<T>(string path, string? token = null, CancellationToken ct = default)
        {
            if (!path.StartsWith("/customers?", StringComparison.OrdinalIgnoreCase))
            {
                throw new NotSupportedException(path);
            }

            if (ThrowOnList)
            {
                throw new InvalidOperationException("offline");
            }

            const string json = """
            {
              "customers": [
                {
                  "id": 1,
                  "display_name": "Acme Solar",
                  "contact_name": "Caleb",
                  "business_name": "Acme",
                  "email": "acme@example.com",
                  "phone": "555-0100",
                  "address": "1 Main",
                  "city": "Indy",
                  "state": "IN",
                  "zip_code": "46204",
                  "is_active": true,
                  "created_at": "2026-03-10T10:00:00Z"
                }
              ]
            }
            """;
            return Task.FromResult(JsonSerializer.Deserialize<T>(json, new JsonSerializerOptions { PropertyNameCaseInsensitive = true })!);
        }

        public Task<T> PostAsync<T>(string path, object? body = null, string? token = null, IDictionary<string, string>? headers = null, CancellationToken ct = default)
        {
            if (path == "/customers")
            {
                PostCalls += 1;
                return Task.FromResult(typeof(T) == typeof(object) ? (T)(object)new object() : JsonSerializer.Deserialize<T>("{}")!);
            }

            throw new NotSupportedException(path);
        }

        public Task<T> PatchAsync<T>(string path, object body, string? token = null, CancellationToken ct = default)
        {
            if (path.StartsWith("/customers/", StringComparison.OrdinalIgnoreCase))
            {
                PatchCalls += 1;
                return Task.FromResult(typeof(T) == typeof(object) ? (T)(object)new object() : JsonSerializer.Deserialize<T>("{}")!);
            }

            throw new NotSupportedException(path);
        }

        public Task DeleteAsync(string path, string? token = null, IDictionary<string, string>? headers = null, CancellationToken ct = default)
        {
            LastDeletePath = path;
            return Task.CompletedTask;
        }
    }

    private sealed class InMemoryCacheRepository : ILocalCacheRepository
    {
        public List<Customer> CachedCustomers { get; } = new();

        public Task UpsertCustomersAsync(IEnumerable<Customer> customers, CancellationToken ct = default)
        {
            CachedCustomers.Clear();
            CachedCustomers.AddRange(customers);
            return Task.CompletedTask;
        }

        public Task<IReadOnlyList<Customer>> GetCustomersAsync(bool includeInactive, string? search, CancellationToken ct = default)
        {
            IEnumerable<Customer> rows = CachedCustomers;
            if (!includeInactive)
            {
                rows = rows.Where(c => c.IsActive);
            }

            if (!string.IsNullOrWhiteSpace(search))
            {
                rows = rows.Where(c => c.DisplayName.Contains(search, StringComparison.OrdinalIgnoreCase));
            }

            return Task.FromResult((IReadOnlyList<Customer>)rows.ToList());
        }

        public Task UpsertPalletAsync(Pallet pallet, CancellationToken ct = default) => Task.CompletedTask;
        public Task<IReadOnlyList<Pallet>> GetPalletsAsync(string status, CancellationToken ct = default) => Task.FromResult((IReadOnlyList<Pallet>)Array.Empty<Pallet>());
        public Task UpsertExportsAsync(IEnumerable<ExportRecord> exports, CancellationToken ct = default) => Task.CompletedTask;
        public Task<IReadOnlyList<ExportRecord>> GetExportsByPalletAsync(int palletId, CancellationToken ct = default) => Task.FromResult((IReadOnlyList<ExportRecord>)Array.Empty<ExportRecord>());
    }

    private sealed class FixedAuthService : IApiTokenProvider
    {
        public Task<string?> GetBearerTokenAsync(CancellationToken ct = default) => Task.FromResult<string?>("token");
    }
}
