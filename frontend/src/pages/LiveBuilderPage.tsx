import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import AppFrame from "../components/layout/AppFrame";
import { useToast } from "../components/notifications/ToastProvider";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import TextInput from "../components/ui/TextInput";
import { listOutboxOperations } from "../sync/outbox";
import {
  repoAddPalletItem,
  repoCompletePallet,
  repoCreatePallet,
  repoGetPallet,
  repoListPallets,
  repoRemovePalletItem,
} from "../features/palletRepo";
import { createExport, type Pallet } from "../features/pallets";
import { listCustomers, type Customer } from "../features/customers";

const PANEL_CAPACITY_OPTIONS = [25, 26, 30, 35] as const;
const TEMPLATE_OPTIONS = ["200WT", "220WT", "220M6", "330WT", "450WT", "450BT"] as const;
const LAST_EXPORT_TEMPLATE_KEY = "pm2_last_export_template";
const CACHED_CUSTOMERS_KEY = "pm2_cached_customers";

function loadLastExportTemplate(): (typeof TEMPLATE_OPTIONS)[number] {
  const raw = localStorage.getItem(LAST_EXPORT_TEMPLATE_KEY);
  if (!raw) {
    return "200WT";
  }
  return (TEMPLATE_OPTIONS.find((item) => item === raw) ?? "200WT") as (typeof TEMPLATE_OPTIONS)[number];
}

function loadCachedCustomers(): Customer[] {
  const raw = localStorage.getItem(CACHED_CUSTOMERS_KEY);
  if (!raw) {
    return [];
  }
  try {
    const parsed = JSON.parse(raw) as Customer[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export default function LiveBuilderPage() {
  const { token } = useAuth();
  const { notify } = useToast();

  const [customers, setCustomers] = useState<Customer[]>(() => loadCachedCustomers());
  const [selectedCustomerId, setSelectedCustomerId] = useState<number | null>(null);

  const [current, setCurrent] = useState<Pallet | null>(null);
  const [serial, setSerial] = useState("");
  const [isBusy, setIsBusy] = useState(false);
  const [queuedOpsCount, setQueuedOpsCount] = useState(0);
  const [activePalletCount, setActivePalletCount] = useState(0);

  const [newMaxPanels, setNewMaxPanels] = useState<number>(25);
  const [exportTemplate, setExportTemplate] = useState<(typeof TEMPLATE_OPTIONS)[number]>(loadLastExportTemplate);

  const serialInputRef = useRef<HTMLInputElement | null>(null);

  const remaining = useMemo(() => {
    if (!current) {
      return 0;
    }
    return current.max_panels - current.item_count;
  }, [current]);

  const activeCustomer = useMemo(() => {
    if (!current || !current.customer_id) {
      return null;
    }
    return customers.find((customer) => customer.id === current.customer_id) ?? null;
  }, [current, customers]);

  const selectedCustomer = useMemo(() => {
    if (!selectedCustomerId) {
      return null;
    }
    return customers.find((customer) => customer.id === selectedCustomerId) ?? null;
  }, [customers, selectedCustomerId]);

  const refreshCustomers = async () => {
    if (!token) {
      return;
    }
    try {
      const response = await listCustomers(token, true);
      setCustomers(response.customers);
      localStorage.setItem(CACHED_CUSTOMERS_KEY, JSON.stringify(response.customers));
      if (selectedCustomerId === null && response.customers.length > 0) {
        setSelectedCustomerId(response.customers[0].id);
      }
    } catch {
      const cached = loadCachedCustomers();
      setCustomers(cached);
      if (selectedCustomerId === null && cached.length > 0) {
        setSelectedCustomerId(cached[0].id);
      }
    }
  };

  const refreshActivePallets = async () => {
    const response = await repoListPallets(token, "active");
    const pallets = response.pallets.slice().sort((a, b) => b.pallet_number - a.pallet_number);
    setActivePalletCount(pallets.length);
    setQueuedOpsCount(listOutboxOperations().length);

    const currentStillActive = current ? pallets.find((pallet) => pallet.id === current.id) : null;
    const nextSelected = currentStillActive?.id ?? pallets[0]?.id ?? null;

    if (nextSelected) {
      const full = await repoGetPallet(token, nextSelected);
      setCurrent(full);
    } else {
      setCurrent(null);
    }
  };

  useEffect(() => {
    void refreshCustomers();
    void refreshActivePallets();
  }, [token]);

  const handleCreatePallet = async (event: FormEvent) => {
    event.preventDefault();
    if (!selectedCustomerId) {
      notify("Select a customer first", "warning");
      return;
    }

    setIsBusy(true);
    try {
      const created = await repoCreatePallet(token, {
        max_panels: newMaxPanels,
        customer_id: selectedCustomerId,
      });
      notify(`Created pallet #${created.pallet_number}`, "success");
      await refreshActivePallets();
      setCurrent(created);
      setSerial("");
      setQueuedOpsCount(listOutboxOperations().length);
      serialInputRef.current?.focus();
    } catch {
      notify("Failed to create pallet", "error");
    } finally {
      setIsBusy(false);
    }
  };

  const handleAddSerial = async (event: FormEvent) => {
    event.preventDefault();
    if (!current) {
      notify("Create an active pallet first", "warning");
      return;
    }

    setIsBusy(true);
    try {
      const updated = await repoAddPalletItem(token, current.id, serial);
      setCurrent(updated);
      setSerial("");
      notify("Serial added", "success");
      setQueuedOpsCount(listOutboxOperations().length);
      serialInputRef.current?.focus();
    } catch {
      notify("Failed to add serial", "error");
    } finally {
      setIsBusy(false);
    }
  };

  const handleRemoveItem = async (itemId: number) => {
    if (!current) {
      return;
    }

    setIsBusy(true);
    try {
      const updated = await repoRemovePalletItem(token, current.id, itemId);
      setCurrent(updated);
      notify("Serial removed", "success");
      setQueuedOpsCount(listOutboxOperations().length);
    } catch {
      notify("Failed to remove serial", "error");
    } finally {
      setIsBusy(false);
    }
  };

  const handleCompleteAndExport = async () => {
    if (!current) {
      return;
    }

    setIsBusy(true);
    try {
      const updated = await repoCompletePallet(token, current.id);
      localStorage.setItem(LAST_EXPORT_TEMPLATE_KEY, exportTemplate);

      if (token) {
        const createdExport = await createExport(token, { pallet_id: updated.id, template_type: exportTemplate });
        notify(
          `Pallet #${updated.pallet_number} completed and export #${createdExport.id} created (${exportTemplate})`,
          "success"
        );
      } else {
        notify("Pallet completed offline. Export will require backend connection.", "warning");
      }

      await refreshActivePallets();
      setQueuedOpsCount(listOutboxOperations().length);
    } catch {
      notify("Failed to complete/export pallet", "error");
    } finally {
      setIsBusy(false);
    }
  };

  return (
    <AppFrame title="Live Builder">
      <section className="builder-grid">
        <Card title="Active pallet">
          {current ? (
            <div className="builder-meta">
              <p>
                <strong>Pallet:</strong> #{current.pallet_number}
              </p>
              <p>
                <strong>Status:</strong> {current.status}
              </p>
              <p>
                <strong>Customer:</strong> {activeCustomer?.display_name ?? current.customer_id ?? "-"}
              </p>
              <p>
                <strong>Capacity:</strong> {current.item_count}/{current.max_panels}
              </p>
              <p>
                <strong>Remaining:</strong> {remaining}
              </p>
              <p>
                <strong>Queued Ops:</strong> {queuedOpsCount}
              </p>
              {activePalletCount > 1 ? (
                <p>
                  <strong>Active Pallets:</strong> {activePalletCount} (using most recent)
                </p>
              ) : null}
            </div>
          ) : (
            <p>No active pallet. Create one to start scanning.</p>
          )}
        </Card>

        <Card title="Create pallet">
          <form className="builder-form" onSubmit={handleCreatePallet}>
            <label className="ui-input-label">
              <span>Customer</span>
              <select
                className="ui-select"
                value={selectedCustomerId ?? ""}
                onChange={(event) => setSelectedCustomerId(event.target.value ? Number(event.target.value) : null)}
              >
                <option value="">Select customer</option>
                {customers.map((customer) => (
                  <option key={customer.id} value={customer.id}>
                    {customer.display_name}
                  </option>
                ))}
              </select>
            </label>

            <label className="ui-input-label">
              <span>Panel count</span>
              <select
                className="ui-select"
                value={newMaxPanels}
                onChange={(event) => setNewMaxPanels(Number(event.target.value))}
              >
                {PANEL_CAPACITY_OPTIONS.map((count) => (
                  <option key={count} value={count}>
                    {count}
                  </option>
                ))}
              </select>
            </label>

            {selectedCustomer ? (
              <div className="builder-meta">
                <p>
                  <strong>Contact:</strong> {selectedCustomer.contact_name ?? "-"}
                </p>
                <p>
                  <strong>Business:</strong> {selectedCustomer.business_name ?? "-"}
                </p>
                <p>
                  <strong>Email:</strong> {selectedCustomer.email ?? "-"}
                </p>
              </div>
            ) : null}

            <Button disabled={isBusy} type="submit">
              Create Active Pallet
            </Button>
          </form>
        </Card>
      </section>

      <section className="builder-grid">
        <Card title="Scan/Add serial">
          <form className="builder-form" onSubmit={handleAddSerial}>
            <TextInput
              label="Serial"
              ref={serialInputRef}
              value={serial}
              onChange={(event) => setSerial(event.target.value.toUpperCase())}
              placeholder="Scan barcode and press Enter"
              required
            />
            <Button disabled={isBusy || !current || remaining <= 0} type="submit">
              Add Serial
            </Button>
          </form>
        </Card>

        <Card title="Complete + export pallet">
          <p>Select panel type at export time (1.1 behavior).</p>
          <label className="ui-input-label">
            <span>Panel type</span>
            <select
              className="ui-select"
              value={exportTemplate}
              onChange={(event) => setExportTemplate(event.target.value as (typeof TEMPLATE_OPTIONS)[number])}
            >
              {TEMPLATE_OPTIONS.map((template) => (
                <option key={template} value={template}>
                  {template}
                </option>
              ))}
            </select>
          </label>
          <Button disabled={isBusy || !current || remaining !== 0} onClick={handleCompleteAndExport}>
            Complete + Export Current Pallet
          </Button>
        </Card>
      </section>

      <section className="card-grid">
        <Card title="Current items">
          {!current || current.items.length === 0 ? (
            <p>No serials added yet.</p>
          ) : (
            <table className="items-table">
              <thead>
                <tr>
                  <th>Slot</th>
                  <th>Serial</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {current.items
                  .slice()
                  .sort((a, b) => a.slot_index - b.slot_index)
                  .map((item) => (
                    <tr key={item.id}>
                      <td>{item.slot_index}</td>
                      <td className="mono">{item.serial}</td>
                      <td>
                        <Button variant="danger" disabled={isBusy} onClick={() => void handleRemoveItem(item.id)}>
                          Remove
                        </Button>
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
