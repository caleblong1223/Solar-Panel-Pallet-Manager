import { FormEvent, useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import AppFrame from "../components/layout/AppFrame";
import { useToast } from "../components/notifications/ToastProvider";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import TextInput from "../components/ui/TextInput";
import {
  createCustomer,
  deleteCustomer,
  listCustomers,
  updateCustomer,
  type Customer,
  type CustomerCreatePayload,
} from "../features/customers";
import { listPalletsForCustomer, type Pallet } from "../features/pallets";
import { loadRuntimeSettings } from "../lib/runtimeConfig";

type EditState = {
  id: number | null;
  form: CustomerCreatePayload;
};

const EMPTY_FORM: CustomerCreatePayload = {
  display_name: "",
  contact_name: "",
  business_name: "",
  email: "",
  phone: "",
  address: "",
  city: "",
  state: "",
  zip_code: "",
  is_active: true,
};

export default function CustomersPage() {
  const { token } = useAuth();
  const { notify } = useToast();

  const [customers, setCustomers] = useState<Customer[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showInactive, setShowInactive] = useState(false);
  const [search, setSearch] = useState("");

  const [editState, setEditState] = useState<EditState>({ id: null, form: EMPTY_FORM });
  const [isSaving, setIsSaving] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const [pallets, setPallets] = useState<Pallet[]>([]);
  const [palletsLoading, setPalletsLoading] = useState(false);
  const [selectedPalletIds, setSelectedPalletIds] = useState<number[]>([]);

  const CUSTOMERS_CACHE_KEY = "pm2_cached_customers";

  const loadCustomers = async () => {
    setIsLoading(true);
    try {
      const response = await listCustomers(token ?? "", {
        isActive: showInactive ? undefined : true,
        search,
      });
      setCustomers(response.customers);
      try {
        localStorage.setItem(CUSTOMERS_CACHE_KEY, JSON.stringify(response.customers));
      } catch {
        // Ignore cache write failures.
      }
    } catch (error) {
      // On network/auth failures, fall back to any cached customers so the page
      // still works offline.
      let usedCache = false;
      try {
        const cachedRaw = localStorage.getItem(CUSTOMERS_CACHE_KEY);
        if (cachedRaw) {
          const parsed = JSON.parse(cachedRaw) as Customer[];
          setCustomers(parsed);
          usedCache = true;
        }
      } catch {
        // Ignore cache parse failures.
      }
      const message =
        error instanceof Error ? error.message : "Failed to load customers";
      if (!usedCache) {
        notify(message, "error");
      } else {
        notify("Using last known customers (offline)", "warning");
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // Hydrate from cache immediately for a fast, offline-friendly experience.
    try {
      const cachedRaw = localStorage.getItem(CUSTOMERS_CACHE_KEY);
      if (cachedRaw) {
        const parsed = JSON.parse(cachedRaw) as Customer[];
        setCustomers(parsed);
      }
    } catch {
      // Ignore cache parse failures.
    }
    void loadCustomers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, showInactive]);

  const startCreate = () => {
    setEditState({ id: null, form: { ...EMPTY_FORM } });
  };

  const startEdit = (customer: Customer) => {
    setEditState({
      id: customer.id,
      form: {
        display_name: customer.display_name,
        contact_name: customer.contact_name ?? "",
        business_name: customer.business_name ?? "",
        email: customer.email ?? "",
        phone: customer.phone ?? "",
        address: customer.address ?? "",
        city: customer.city ?? "",
        state: customer.state ?? "",
        zip_code: customer.zip_code ?? "",
        is_active: customer.is_active,
      },
    });
  };

  const handleSave = async (event: FormEvent) => {
    event.preventDefault();
    const payload: CustomerCreatePayload = {
      ...editState.form,
      display_name: editState.form.display_name.trim(),
    };
    if (!payload.display_name) {
      notify("Display name is required", "warning");
      return;
    }
    setIsSaving(true);
    try {
      if (editState.id == null) {
        await createCustomer(token ?? "", payload);
        notify("Customer created", "success");
      } else {
        await updateCustomer(token ?? "", editState.id, payload);
        notify("Customer updated", "success");
      }
      setEditState({ id: null, form: EMPTY_FORM });
      await loadCustomers();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to save customer";
      notify(message, "error");
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeactivate = async (customer: Customer) => {
    if (!token) return;
    if (!window.confirm(`Archive customer "${customer.display_name}"?`)) {
      return;
    }
    try {
      await deleteCustomer(token ?? "", customer.id);
      notify("Customer archived", "success");
      await loadCustomers();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to archive customer";
      notify(message, "error");
    }
  };

  const handleRefresh = async (event: FormEvent) => {
    event.preventDefault();
    await loadCustomers();
  };

  const handleViewPallets = async (customer: Customer) => {
    setSelectedCustomer(customer);
    setPallets([]);
    setSelectedPalletIds([]);
    setPalletsLoading(true);
    try {
      const response = await listPalletsForCustomer(token ?? "", customer.id, { includeDeleted: false });
      setPallets(response.pallets);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to load pallets for customer";
      notify(message, "error");
    } finally {
      setPalletsLoading(false);
    }
  };

  const togglePalletSelection = (palletId: number) => {
    setSelectedPalletIds((prev) =>
      prev.includes(palletId) ? prev.filter((id) => id !== palletId) : [...prev, palletId]
    );
  };

  const handleDownloadExcel = async () => {
    if (!token) {
      notify("Unable to download without a connection to the server.", "warning");
      return;
    }
    if (selectedPalletIds.length !== 1) {
      notify("Select exactly one pallet to download Excel.", "warning");
      return;
    }
    const { apiBaseUrl } = loadRuntimeSettings();
    const palletId = selectedPalletIds[0];
    try {
      const response = await fetch(`${apiBaseUrl}/pallets/${palletId}/excel`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        throw new Error(`Excel download failed with status ${response.status}`);
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `pallet-${palletId}.xlsx`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to download Excel";
      notify(message, "error");
    }
  };

  const handleCombinedPdf = async () => {
    if (!token) {
      notify("Unable to generate PDF without a connection to the server.", "warning");
      return;
    }
    if (selectedPalletIds.length === 0) {
      notify("Select at least one pallet to create a combined PDF.", "warning");
      return;
    }
    const { apiBaseUrl } = loadRuntimeSettings();
    try {
      const response = await fetch(`${apiBaseUrl}/pallets/combined-pdf`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(selectedPalletIds),
      });
      if (!response.ok) {
        throw new Error(`Combined PDF failed with status ${response.status}`);
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to generate combined PDF";
      notify(message, "error");
    }
  };

  return (
    <AppFrame title="Customers">
      <section className="builder-grid">
        <Card title={editState.id == null ? "New customer" : `Edit customer #${editState.id}`}>
          <form className="builder-form" onSubmit={handleSave}>
            <TextInput
              label="Display name"
              value={editState.form.display_name}
              onChange={(event) =>
                setEditState((prev) => ({
                  ...prev,
                  form: { ...prev.form, display_name: event.target.value },
                }))
              }
              required
            />
            <TextInput
              label="Business name"
              value={editState.form.business_name ?? ""}
              onChange={(event) =>
                setEditState((prev) => ({
                  ...prev,
                  form: { ...prev.form, business_name: event.target.value },
                }))
              }
            />
            <TextInput
              label="Contact name"
              value={editState.form.contact_name ?? ""}
              onChange={(event) =>
                setEditState((prev) => ({
                  ...prev,
                  form: { ...prev.form, contact_name: event.target.value },
                }))
              }
            />
            <TextInput
              label="Email"
              type="email"
              value={editState.form.email ?? ""}
              onChange={(event) =>
                setEditState((prev) => ({
                  ...prev,
                  form: { ...prev.form, email: event.target.value },
                }))
              }
            />
            <TextInput
              label="Phone"
              value={editState.form.phone ?? ""}
              onChange={(event) =>
                setEditState((prev) => ({
                  ...prev,
                  form: { ...prev.form, phone: event.target.value },
                }))
              }
            />
            <TextInput
              label="Address"
              value={editState.form.address ?? ""}
              onChange={(event) =>
                setEditState((prev) => ({
                  ...prev,
                  form: { ...prev.form, address: event.target.value },
                }))
              }
            />
            <TextInput
              label="City"
              value={editState.form.city ?? ""}
              onChange={(event) =>
                setEditState((prev) => ({
                  ...prev,
                  form: { ...prev.form, city: event.target.value },
                }))
              }
            />
            <TextInput
              label="State"
              value={editState.form.state ?? ""}
              onChange={(event) =>
                setEditState((prev) => ({
                  ...prev,
                  form: { ...prev.form, state: event.target.value },
                }))
              }
            />
            <TextInput
              label="ZIP code"
              value={editState.form.zip_code ?? ""}
              onChange={(event) =>
                setEditState((prev) => ({
                  ...prev,
                  form: { ...prev.form, zip_code: event.target.value },
                }))
              }
            />

            <label className="ui-checkbox">
              <input
                type="checkbox"
                checked={editState.form.is_active ?? true}
                onChange={(event) =>
                  setEditState((prev) => ({
                    ...prev,
                    form: { ...prev.form, is_active: event.target.checked },
                  }))
                }
              />
              Active
            </label>

            <div style={{ display: "flex", gap: "8px", marginTop: "8px" }}>
              <Button type="submit" disabled={isSaving}>
                {editState.id == null ? "Create customer" : "Save changes"}
              </Button>
              {editState.id != null ? (
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => setEditState({ id: null, form: EMPTY_FORM })}
                  disabled={isSaving}
                >
                  Cancel edit
                </Button>
              ) : null}
            </div>
          </form>
        </Card>

        <Card title="Customer list">
          <form className="builder-form" onSubmit={handleRefresh}>
            <TextInput
              label="Search by name"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Start typing to filter..."
            />
            <label className="ui-checkbox">
              <input
                type="checkbox"
                checked={showInactive}
                onChange={(event) => setShowInactive(event.target.checked)}
              />
              Show inactive/archived
            </label>
            <div style={{ display: "flex", gap: "8px" }}>
              <Button type="submit" disabled={isLoading}>
                Refresh
              </Button>
              <Button type="button" variant="secondary" onClick={startCreate}>
                New customer
              </Button>
            </div>
          </form>

          {isLoading ? (
            <p>Loading customers...</p>
          ) : customers.length === 0 ? (
            <p style={{ marginTop: "12px", color: "var(--color-text-secondary)" }}>
              No customers found.
            </p>
          ) : (
            <table className="items-table" style={{ marginTop: "12px" }}>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Business</th>
                  <th>Contact</th>
                  <th>Phone</th>
                  <th>City/State</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {customers.map((c) => (
                  <tr key={c.id}>
                    <td>{c.display_name}</td>
                    <td>{c.business_name}</td>
                    <td>{c.contact_name}</td>
                    <td>{c.phone}</td>
                    <td>
                      {c.city}
                      {c.state ? (c.city ? `, ${c.state}` : c.state) : ""}
                    </td>
                    <td>{c.is_active ? "Active" : "Archived"}</td>
                    <td style={{ textAlign: "right" }}>
                      <Button
                        variant="secondary"
                        onClick={() => startEdit(c)}
                        style={{ marginRight: "4px" }}
                      >
                        Edit
                      </Button>
                      <Button
                        variant="secondary"
                        onClick={() => void handleViewPallets(c)}
                        style={{ marginRight: "4px" }}
                      >
                        View pallets
                      </Button>
                      {c.is_active ? (
                        <Button variant="danger" onClick={() => void handleDeactivate(c)}>
                          Archive
                        </Button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        <Card title={selectedCustomer ? `Pallets for ${selectedCustomer.display_name}` : "Pallets by customer"}>
          {selectedCustomer == null ? (
            <p style={{ marginTop: "12px", color: "var(--color-text-secondary)" }}>
              Select a customer and choose &quot;View pallets&quot; to see their pallets.
            </p>
          ) : palletsLoading ? (
            <p>Loading pallets...</p>
          ) : pallets.length === 0 ? (
            <p style={{ marginTop: "12px", color: "var(--color-text-secondary)" }}>
              No pallets found for this customer.
            </p>
          ) : (
            <>
              <div style={{ display: "flex", gap: "8px", marginTop: "8px", marginBottom: "8px" }}>
                <Button type="button" variant="secondary" onClick={() => void handleDownloadExcel()}>
                  Download Excel (selected)
                </Button>
                <Button type="button" variant="primary" onClick={() => void handleCombinedPdf()}>
                  Combined PDF (selected)
                </Button>
              </div>
              <table className="items-table" style={{ marginTop: "12px" }}>
                <thead>
                  <tr>
                    <th />
                    <th>Pallet #</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Completed</th>
                    <th>Items</th>
                  </tr>
                </thead>
                <tbody>
                  {pallets.map((pallet) => (
                    <tr key={pallet.id}>
                      <td>
                        <input
                          type="checkbox"
                          checked={selectedPalletIds.includes(pallet.id)}
                          onChange={() => togglePalletSelection(pallet.id)}
                        />
                      </td>
                      <td>{pallet.pallet_number}</td>
                      <td>{pallet.status}</td>
                      <td>{new Date(pallet.created_at).toLocaleString()}</td>
                      <td>{pallet.completed_at ? new Date(pallet.completed_at).toLocaleString() : "-"}</td>
                      <td>{pallet.item_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </Card>
      </section>
    </AppFrame>
  );
}

