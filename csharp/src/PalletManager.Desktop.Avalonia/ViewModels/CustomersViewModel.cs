using System.Collections.ObjectModel;
using System.Text.Json.Serialization;
using PalletManager.Application.Contracts;
using PalletManager.Domain.Entities;

namespace PalletManager.Desktop.Avalonia.ViewModels;

public sealed class CustomersViewModel : ViewModelBase
{
    private readonly IApiClient _apiClient;
    private readonly IAuthService _authService;
    private readonly ILocalCacheRepository _cacheRepository;

    private int? _editingCustomerId;
    private string _displayName = string.Empty;
    private string _contactName = string.Empty;
    private string _businessName = string.Empty;
    private string _email = string.Empty;
    private string _phone = string.Empty;
    private string _address = string.Empty;
    private string _city = string.Empty;
    private string _state = string.Empty;
    private string _zipCode = string.Empty;
    private bool _isActive = true;
    private bool _showInactive;
    private string _search = string.Empty;
    private string _statusMessage = string.Empty;
    private bool _isLoading;
    private bool _isSaving;

    public CustomersViewModel(
        IApiClient apiClient,
        IAuthService authService,
        ILocalCacheRepository cacheRepository)
    {
        _apiClient = apiClient;
        _authService = authService;
        _cacheRepository = cacheRepository;
        Customers = new ObservableCollection<Customer>();
    }

    public ObservableCollection<Customer> Customers { get; }

    public bool IsEditing => _editingCustomerId.HasValue;

    public string DisplayName
    {
        get => _displayName;
        set => SetProperty(ref _displayName, value);
    }

    public string ContactName
    {
        get => _contactName;
        set => SetProperty(ref _contactName, value);
    }

    public string BusinessName
    {
        get => _businessName;
        set => SetProperty(ref _businessName, value);
    }

    public string Email
    {
        get => _email;
        set => SetProperty(ref _email, value);
    }

    public string Phone
    {
        get => _phone;
        set => SetProperty(ref _phone, value);
    }

    public string Address
    {
        get => _address;
        set => SetProperty(ref _address, value);
    }

    public string City
    {
        get => _city;
        set => SetProperty(ref _city, value);
    }

    public string State
    {
        get => _state;
        set => SetProperty(ref _state, value);
    }

    public string ZipCode
    {
        get => _zipCode;
        set => SetProperty(ref _zipCode, value);
    }

    public bool IsActive
    {
        get => _isActive;
        set => SetProperty(ref _isActive, value);
    }

    public bool ShowInactive
    {
        get => _showInactive;
        set => SetProperty(ref _showInactive, value);
    }

    public string Search
    {
        get => _search;
        set => SetProperty(ref _search, value);
    }

    public string StatusMessage
    {
        get => _statusMessage;
        private set => SetProperty(ref _statusMessage, value);
    }

    public bool IsLoading
    {
        get => _isLoading;
        private set => SetProperty(ref _isLoading, value);
    }

    public bool IsSaving
    {
        get => _isSaving;
        private set => SetProperty(ref _isSaving, value);
    }

    public async Task RefreshAsync(CancellationToken ct = default)
    {
        IsLoading = true;
        try
        {
            var token = await _authService.GetTokenAsync(ct) ?? string.Empty;
            try
            {
                var query = BuildListQuery();
                var response = await _apiClient.GetAsync<CustomerListResponse>($"/customers?{query}", token, ct);
                var mapped = response.Customers.Select(MapCustomer).ToList();
                await _cacheRepository.UpsertCustomersAsync(mapped, ct);
                SetCustomers(mapped);
                StatusMessage = $"Loaded {mapped.Count} customer(s) from API.";
            }
            catch
            {
                var cached = await _cacheRepository.GetCustomersAsync(ShowInactive, Search, ct);
                SetCustomers(cached);
                StatusMessage = "Using cached customers (offline).";
            }
        }
        finally
        {
            IsLoading = false;
        }
    }

    public void StartCreate()
    {
        _editingCustomerId = null;
        ResetForm();
        RaisePropertyChanged(nameof(IsEditing));
    }

    public void StartEdit(int customerId)
    {
        var customer = Customers.FirstOrDefault(c => c.Id == customerId);
        if (customer is null)
        {
            return;
        }

        _editingCustomerId = customer.Id;
        DisplayName = customer.DisplayName;
        ContactName = customer.ContactName ?? string.Empty;
        BusinessName = customer.BusinessName ?? string.Empty;
        Email = customer.Email ?? string.Empty;
        Phone = customer.Phone ?? string.Empty;
        Address = customer.Address ?? string.Empty;
        City = customer.City ?? string.Empty;
        State = customer.State ?? string.Empty;
        ZipCode = customer.ZipCode ?? string.Empty;
        IsActive = customer.IsActive;
        RaisePropertyChanged(nameof(IsEditing));
    }

    public async Task SaveAsync(CancellationToken ct = default)
    {
        var name = DisplayName.Trim();
        if (string.IsNullOrWhiteSpace(name))
        {
            StatusMessage = "Display name is required.";
            return;
        }

        IsSaving = true;
        try
        {
            var token = await _authService.GetTokenAsync(ct) ?? string.Empty;
            var payload = new Dictionary<string, object?>
            {
                ["display_name"] = name,
                ["contact_name"] = ToNullIfEmpty(ContactName),
                ["business_name"] = ToNullIfEmpty(BusinessName),
                ["email"] = ToNullIfEmpty(Email),
                ["phone"] = ToNullIfEmpty(Phone),
                ["address"] = ToNullIfEmpty(Address),
                ["city"] = ToNullIfEmpty(City),
                ["state"] = ToNullIfEmpty(State),
                ["zip_code"] = ToNullIfEmpty(ZipCode),
                ["is_active"] = IsActive,
            };

            if (_editingCustomerId.HasValue)
            {
                _ = await _apiClient.PatchAsync<object>($"/customers/{_editingCustomerId.Value}", payload, token, ct);
                StatusMessage = "Customer updated.";
            }
            else
            {
                _ = await _apiClient.PostAsync<object>("/customers", payload, token, null, ct);
                StatusMessage = "Customer created.";
            }

            StartCreate();
            await RefreshAsync(ct);
        }
        catch (Exception ex)
        {
            StatusMessage = $"Failed to save customer: {ex.Message}";
        }
        finally
        {
            IsSaving = false;
        }
    }

    public async Task ArchiveAsync(int customerId, CancellationToken ct = default)
    {
        try
        {
            var token = await _authService.GetTokenAsync(ct) ?? string.Empty;
            await _apiClient.DeleteAsync($"/customers/{customerId}", token, null, ct);
            StatusMessage = "Customer archived.";
            await RefreshAsync(ct);
        }
        catch (Exception ex)
        {
            StatusMessage = $"Failed to archive customer: {ex.Message}";
        }
    }

    private string BuildListQuery()
    {
        var values = new List<string> { "limit=200", "offset=0" };
        if (!ShowInactive)
        {
            values.Add("is_active=true");
        }

        var search = Search.Trim();
        if (!string.IsNullOrWhiteSpace(search))
        {
            values.Add($"search={Uri.EscapeDataString(search)}");
        }

        return string.Join("&", values);
    }

    private static Customer MapCustomer(ApiCustomer dto)
    {
        return new Customer
        {
            Id = dto.Id,
            DisplayName = dto.DisplayName,
            ContactName = dto.ContactName,
            BusinessName = dto.BusinessName,
            Email = dto.Email,
            Phone = dto.Phone,
            Address = dto.Address,
            City = dto.City,
            State = dto.State,
            ZipCode = dto.ZipCode,
            IsActive = dto.IsActive,
            CreatedAtUtc = dto.CreatedAt,
        };
    }

    private void SetCustomers(IEnumerable<Customer> customers)
    {
        Customers.Clear();
        foreach (var customer in customers)
        {
            Customers.Add(customer);
        }
    }

    private void ResetForm()
    {
        DisplayName = string.Empty;
        ContactName = string.Empty;
        BusinessName = string.Empty;
        Email = string.Empty;
        Phone = string.Empty;
        Address = string.Empty;
        City = string.Empty;
        State = string.Empty;
        ZipCode = string.Empty;
        IsActive = true;
    }

    private static string? ToNullIfEmpty(string value)
    {
        var trimmed = value.Trim();
        return string.IsNullOrWhiteSpace(trimmed) ? null : trimmed;
    }

    private sealed class CustomerListResponse
    {
        [JsonPropertyName("customers")]
        public List<ApiCustomer> Customers { get; set; } = new();
    }

    private sealed class ApiCustomer
    {
        [JsonPropertyName("id")]
        public int Id { get; set; }

        [JsonPropertyName("display_name")]
        public string DisplayName { get; set; } = string.Empty;

        [JsonPropertyName("contact_name")]
        public string? ContactName { get; set; }

        [JsonPropertyName("business_name")]
        public string? BusinessName { get; set; }

        [JsonPropertyName("email")]
        public string? Email { get; set; }

        [JsonPropertyName("phone")]
        public string? Phone { get; set; }

        [JsonPropertyName("address")]
        public string? Address { get; set; }

        [JsonPropertyName("city")]
        public string? City { get; set; }

        [JsonPropertyName("state")]
        public string? State { get; set; }

        [JsonPropertyName("zip_code")]
        public string? ZipCode { get; set; }

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; }

        [JsonPropertyName("created_at")]
        public DateTime? CreatedAt { get; set; }
    }
}
