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
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  const [showInactive, setShowInactive] = useState(false);
  const [search, setSearch] = useState("");

  const [editState, setEditState] = useState<EditState>({ id: null, form: EMPTY_FORM });
  const [isSaving, setIsSaving] = useState(false);

  const CUSTOMERS_CACHE_KEY = "pm2_cached_customers";

  const loadCustomers = async () => {
    if (!hasLoadedOnce) {
      setIsLoading(true);
    }
    try {
      const response = await listCustomers(token ?? "", {
        isActive: showInactive ? undefined : true,
        search,
      });
      setCustomers(response.customers);
      setHasLoadedOnce(true);
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
      setHasLoadedOnce(true);
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
  }, [showInactive]);

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

  return (
    <AppFrame title="Customers">
      <section className="customers-layout">
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

          {!hasLoadedOnce && isLoading ? (
            <p>Loading customers...</p>
          ) : customers.length === 0 ? (
            <p style={{ marginTop: "12px", color: "var(--color-text-secondary)" }}>
              No customers found.
            </p>
          ) : (
            <table className="items-table customers-table" style={{ marginTop: "12px" }}>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Business</th>
                  <th>Contact</th>
                  <th>Phone</th>
                  <th>Address</th>
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
                    <td>{c.address}</td>
                    <td>
                      {c.city}
                      {c.state ? (c.city ? `, ${c.state}` : c.state) : ""}
                    </td>
                    <td>{c.is_active ? "Active" : "Archived"}</td>
                    <td className="customer-actions-cell">
                      <Button
                        variant="secondary"
                        onClick={() => startEdit(c)}
                      >
                        Edit
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
      </section>
    </AppFrame>
  );
}

