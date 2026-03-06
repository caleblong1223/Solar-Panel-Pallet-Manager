import { FormEvent, useEffect, useRef, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import AppFrame from "../components/layout/AppFrame";
import { useToast } from "../components/notifications/ToastProvider";
import AnimatedSelect, { type AnimatedSelectOption } from "../components/ui/AnimatedSelect";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import TextInput from "../components/ui/TextInput";
import {
  addPalletItem as apiAddPalletItem,
  completePallet as apiCompletePallet,
  createExport,
  createPallet as apiCreatePallet,
  updatePallet,
  type PalletItem,
  type Pallet,
} from "../features/pallets";
import { getExportDownloadUrl } from "../features/exports";
import { listCustomers, type Customer } from "../features/customers";

const DEFAULT_MAX_PANELS = 25;
const TEMPLATE_OPTIONS = ["200WT", "220WT", "220M6", "330WT", "450WT", "450BT"];
const ACCESS_TOKEN_KEY = "pm2_access_token";
const PALLET_SIZES = [25, 26, 30, 35];
const CUSTOMERS_CACHE_KEY = "pm2_cached_customers";
const SESSION_SELECTION_KEY = "pm2_builder_last_selection";
const ACTIVE_PALLET_KEY = "pm2_builder_active_pallet";
let draftPalletCounter = 1;
let draftItemCounter = 1;

function getEffectiveToken(contextToken: string | null): string | null {
  return contextToken ?? localStorage.getItem(ACCESS_TOKEN_KEY);
}

type BuilderSelection = {
  customerId: number | "none";
  template: string;
  size: number;
};

function loadLastBuilderSelection(): BuilderSelection | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const raw = sessionStorage.getItem(SESSION_SELECTION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as BuilderSelection;
    if (!parsed) return null;
    return parsed;
  } catch {
    return null;
  }
}

function persistLastBuilderSelection(value: BuilderSelection) {
  if (typeof window === "undefined") {
    return;
  }
  try {
    sessionStorage.setItem(SESSION_SELECTION_KEY, JSON.stringify(value));
  } catch {
    // ignore
  }
}

function loadActivePallet(): Pallet | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const raw = sessionStorage.getItem(ACTIVE_PALLET_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as Pallet;
  } catch {
    return null;
  }
}

function persistActivePallet(value: Pallet | null) {
  if (typeof window === "undefined") {
    return;
  }
  try {
    if (value === null) {
      sessionStorage.removeItem(ACTIVE_PALLET_KEY);
    } else {
      sessionStorage.setItem(ACTIVE_PALLET_KEY, JSON.stringify(value));
    }
  } catch {
    // ignore storage failures
  }
}

export default function LiveBuilderPage() {
  const { token: contextToken } = useAuth();
  const token = getEffectiveToken(contextToken);
  const { notify } = useToast();

  const [current, setCurrent] = useState<Pallet | null>(() => loadActivePallet());
  const [serial, setSerial] = useState("");
  const [isBusy, setIsBusy] = useState(false);
  const storedSelection = loadLastBuilderSelection();
  const [newPalletTemplate, setNewPalletTemplate] = useState(
    storedSelection && TEMPLATE_OPTIONS.includes(storedSelection.template)
      ? storedSelection.template
      : TEMPLATE_OPTIONS[0]
  );
  const [newPalletSize, setNewPalletSize] = useState<number>(
    storedSelection && PALLET_SIZES.includes(storedSelection.size) ? storedSelection.size : DEFAULT_MAX_PANELS
  );
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [selectedCustomerId, setSelectedCustomerId] = useState<number | "none">(
    storedSelection ? storedSelection.customerId : "none"
  );
  useEffect(() => {
    persistLastBuilderSelection({
      customerId: selectedCustomerId,
      template: newPalletTemplate,
      size: newPalletSize,
    });
  }, [selectedCustomerId, newPalletTemplate, newPalletSize]);
  const [palletNumberDraft, setPalletNumberDraft] = useState<string>("");
  const [isPalletNumberAnimating, setIsPalletNumberAnimating] = useState(false);
  const [isPackoutDateAnimating, setIsPackoutDateAnimating] = useState(false);
  const [packoutDate, setPackoutDate] = useState<string>(() => {
    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, "0");
    const day = String(today.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  });
  const serialInputRef = useRef<HTMLInputElement | null>(null);
  const packoutDateRef = useRef<HTMLInputElement | null>(null);

  const remaining = current ? current.max_panels - current.item_count : 0;

  useEffect(() => {
    if (current) {
      setPalletNumberDraft(String(current.pallet_number));
    } else {
      setPalletNumberDraft("");
    }
  }, [current]);

  useEffect(() => {
    if (!current) return;
    setIsPalletNumberAnimating(true);
    const timeoutId = window.setTimeout(() => setIsPalletNumberAnimating(false), 180);
    return () => window.clearTimeout(timeoutId);
  }, [palletNumberDraft, current]);

  useEffect(() => {
    persistActivePallet(current);
  }, [current]);

  useEffect(() => {
    // Seed from any cached customers first so offline builder still has a usable dropdown.
    try {
      const cachedRaw = localStorage.getItem(CUSTOMERS_CACHE_KEY);
      if (cachedRaw) {
        const parsed = JSON.parse(cachedRaw) as Customer[];
        setCustomers(parsed);
        const legacyDefault = parsed.find((customer) => {
          const name = (customer.display_name ?? "").toLowerCase();
          return name.includes("josh") && name.includes("future") && name.includes("solution");
        });
        if (legacyDefault) {
          setSelectedCustomerId((prev) => (prev === "none" ? legacyDefault.id : prev));
        }
      }
    } catch {
      // Ignore cache parse failures.
    }

    const t = getEffectiveToken(contextToken);
    void listCustomers(t ?? "", { isActive: true })
      .then((response) => {
        setCustomers(response.customers);
        try {
          localStorage.setItem(CUSTOMERS_CACHE_KEY, JSON.stringify(response.customers));
        } catch {
          // Ignore cache write failures.
        }
        // Prefer the legacy default customer if present.
        const legacyDefault = response.customers.find((customer) => {
          const name = (customer.display_name ?? "").toLowerCase();
          return name.includes("josh") && name.includes("future") && name.includes("solution");
        });
        if (legacyDefault) {
          setSelectedCustomerId((prev) => (prev === "none" ? legacyDefault.id : prev));
        }
      })
      .catch(() => {
        // Customers are optional for pallet creation; swallow errors here and surface via explicit actions if needed.
      });
  }, [contextToken]);

  const handleStartNewPallet = async () => {
    setIsBusy(true);
    try {
      const created: Pallet = {
        id: -draftPalletCounter,
        pallet_number: Number(palletNumberDraft) > 0 ? Number(palletNumberDraft) : draftPalletCounter,
        status: "active",
        template_type: newPalletTemplate,
        max_panels: newPalletSize,
        customer_id: selectedCustomerId === "none" ? null : selectedCustomerId,
        created_by: null,
        completed_by: null,
        created_at: new Date().toISOString(),
        completed_at: null,
        deleted_at: null,
        item_count: 0,
        items: [],
      };
      draftPalletCounter += 1;
      setCurrent(created);
      setSerial("");
      notify(`Pallet #${created.pallet_number} started`, "success");
      serialInputRef.current?.focus();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to start pallet";
      notify(message, "error");
    } finally {
      setIsBusy(false);
    }
  };

  const handleAddSerial = async (event: FormEvent) => {
    event.preventDefault();
    if (!current) {
      notify("Start a pallet first", "warning");
      return;
    }
    const s = serial.trim();
    if (!s) return;

    if (remaining <= 0) {
      notify("Pallet is full. Complete it first.", "warning");
      return;
    }

    setIsBusy(true);
    try {
      if (current.items.some((item) => item.serial === s)) {
        notify("Serial already on pallet", "warning");
        return;
      }
      const nextSlot = current.items.length + 1;
      const item: PalletItem = {
        id: -draftItemCounter,
        serial: s,
        slot_index: nextSlot,
        added_by: null,
        added_at: new Date().toISOString(),
      };
      draftItemCounter += 1;
      const updated: Pallet = {
        ...current,
        item_count: current.item_count + 1,
        items: [...current.items, item],
      };
      setCurrent(updated);
      setSerial("");
      notify("Added", "success");
      serialInputRef.current?.focus();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to add serial";
      notify(message, "error");
    } finally {
      setIsBusy(false);
    }
  };

  const handleRemoveItem = async (itemId: number) => {
    if (!current) return;
    setIsBusy(true);
    try {
      const remainingItems = current.items
        .filter((item) => item.id !== itemId)
        .map((item, index) => ({ ...item, slot_index: index + 1 }));
      const updated: Pallet = {
        ...current,
        item_count: remainingItems.length,
        items: remainingItems,
      };
      setCurrent(updated);
      notify("Removed", "success");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to remove";
      notify(message, "error");
    } finally {
      setIsBusy(false);
    }
  };

  const handleComplete = async () => {
    if (!current) return;
    if (remaining !== 0) {
      notify("Pallet must be full to complete", "warning");
      return;
    }
    if (!token) {
      notify("Server connection is required to finalize and export a pallet", "error");
      return;
    }
    const desiredTemplateType = newPalletTemplate;
    const desiredCustomerId = selectedCustomerId === "none" ? null : selectedCustomerId;
    const desiredMaxPanels = newPalletSize;
    const desiredPalletNumber = Number(palletNumberDraft);
    let workingPallet = current;
    const palletNumber = current.pallet_number;

    setIsBusy(true);
    try {
      const createdServerPallet = await apiCreatePallet(token, {
        max_panels: desiredMaxPanels,
        template_type: desiredTemplateType,
        customer_id: desiredCustomerId ?? undefined,
      });
      workingPallet = createdServerPallet;

      const draftItems = current.items
        .slice()
        .sort((a, b) => a.slot_index - b.slot_index);
      for (const item of draftItems) {
        workingPallet = await apiAddPalletItem(token, workingPallet.id, item.serial);
      }

      if (
        Number.isFinite(desiredPalletNumber) &&
        desiredPalletNumber > 0 &&
        workingPallet.pallet_number !== desiredPalletNumber
      ) {
        workingPallet = await updatePallet(token, workingPallet.id, {
          pallet_number: desiredPalletNumber,
        });
      }

      workingPallet = await apiCompletePallet(token, workingPallet.id);
      setCurrent(workingPallet);
      const created = await createExport(token ?? "", {
        pallet_id: workingPallet.id,
        template_type: desiredTemplateType,
        packout_date: packoutDate || undefined,
      });
      const { download_url } = await getExportDownloadUrl(token ?? "", created.id, "xlsx");
      window.open(download_url, "_blank", "noopener,noreferrer");
      notify(`Pallet #${palletNumber} completed · export ready`, "success");
      setCurrent(null);
      serialInputRef.current?.focus();
    } catch {
      notify("Failed to complete or export pallet", "error");
    } finally {
      setIsBusy(false);
    }
  };

  const handleActivePalletSizeChange = (nextSizeRaw: string) => {
    const parsed = Number(nextSizeRaw);
    if (!Number.isFinite(parsed) || parsed <= 0) return;
    if (current && parsed < current.item_count) {
      notify(`Pallet size cannot be lower than current panel count (${current.item_count})`, "warning");
      return;
    }
    setNewPalletSize(parsed);
    if (current) {
      setCurrent({ ...current, max_panels: parsed });
    }
  };

  const bumpPalletNumber = (delta: number) => {
    if (!current) return;
    const parsed = Number(palletNumberDraft || current.pallet_number);
    if (!Number.isFinite(parsed)) return;
    const next = Math.max(1, Math.trunc(parsed + delta));
    setPalletNumberDraft(String(next));
  };

  const bumpPackoutDate = (deltaDays: number) => {
    const base = packoutDate ? new Date(`${packoutDate}T00:00:00`) : new Date();
    if (Number.isNaN(base.getTime())) return;
    base.setDate(base.getDate() + deltaDays);
    const yyyy = base.getFullYear();
    const mm = String(base.getMonth() + 1).padStart(2, "0");
    const dd = String(base.getDate()).padStart(2, "0");
    setPackoutDate(`${yyyy}-${mm}-${dd}`);
    setIsPackoutDateAnimating(true);
    window.setTimeout(() => setIsPackoutDateAnimating(false), 180);
  };

  const commitPalletNumber = async () => {
    if (!current) return;
    const parsed = Number(palletNumberDraft);
    if (!Number.isInteger(parsed) || parsed <= 0) {
      setPalletNumberDraft(String(current.pallet_number));
      notify("Pallet number must be a positive whole number", "warning");
      return;
    }
    if (parsed === current.pallet_number) return;

    // Draft-only while building; server update happens at finalize/export.
    setCurrent({ ...current, pallet_number: parsed });
    notify(`Pallet number set to #${parsed}`, "success");
  };

  return (
    <AppFrame title="Builder">
      {current ? (
        <section className="builder-active-header">
          <label className="builder-active-pill builder-active-pill--input">
            <span className="builder-active-pill__label">Pallet</span>
            <input
              className={
                isPalletNumberAnimating
                  ? "builder-active-pill__number builder-active-pill__number--push"
                  : "builder-active-pill__number"
              }
              type="number"
              min={1}
              value={palletNumberDraft}
              style={{ width: `${Math.max(3, palletNumberDraft.length + 1)}ch` }}
              onChange={(event) => setPalletNumberDraft(event.target.value)}
              onBlur={() => void commitPalletNumber()}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  void commitPalletNumber();
                }
              }}
            />
            <div className="builder-active-pill__stepper" aria-hidden="true">
              <button type="button" onClick={() => bumpPalletNumber(1)}>▲</button>
              <button type="button" onClick={() => bumpPalletNumber(-1)}>▼</button>
            </div>
          </label>
          <AnimatedSelect
            label="Customer"
            value={selectedCustomerId === "none" ? "" : String(selectedCustomerId)}
            placeholder="No customer selected"
            options={[
              { value: "", label: "No customer selected" },
              ...customers.map<AnimatedSelectOption>((customer) => ({
                value: String(customer.id),
                label: customer.display_name,
              })),
            ]}
            onChange={(next) => {
              if (!next) {
                setSelectedCustomerId("none");
              } else {
                setSelectedCustomerId(Number(next));
              }
            }}
            variant="pill"
            className="builder-active-control builder-active-control--customer"
          />
          <AnimatedSelect
            label="Panel Type"
            value={newPalletTemplate}
            options={TEMPLATE_OPTIONS.map<AnimatedSelectOption>((t) => ({
              value: t,
              label: t,
            }))}
            onChange={(next) => setNewPalletTemplate(next)}
            variant="pill"
            className="builder-active-control builder-active-control--panel"
          />
          <AnimatedSelect
            label="Pallet Size"
            value={String(newPalletSize)}
            options={PALLET_SIZES.map<AnimatedSelectOption>((size) => ({
              value: String(size),
              label: `${size} panels`,
            }))}
            onChange={handleActivePalletSizeChange}
            variant="pill"
            className="builder-active-control builder-active-control--size"
          />
          <label className="builder-active-pill builder-active-pill--input builder-active-control builder-active-control--date">
            <span className="builder-active-pill__label">Packout date</span>
            <input
              ref={packoutDateRef}
              className={
                isPackoutDateAnimating
                  ? "builder-active-pill__date builder-active-pill__date--push"
                  : "builder-active-pill__date"
              }
              type="date"
              value={packoutDate}
              onClick={() => packoutDateRef.current?.showPicker?.()}
              onChange={(event) => {
                setPackoutDate(event.target.value);
                window.setTimeout(() => event.currentTarget.blur(), 0);
              }}
            />
            <div className="builder-active-pill__stepper" aria-hidden="true">
              <button type="button" onClick={() => bumpPackoutDate(1)}>▲</button>
              <button type="button" onClick={() => bumpPackoutDate(-1)}>▼</button>
            </div>
          </label>
        </section>
      ) : null}
      <section className="builder-grid">
        <Card
          title={
            current
              ? `Active pallet · ${current.item_count}/${current.max_panels}${remaining > 0 ? ` · ${remaining} remaining` : ""}`
              : "No active pallet"
          }
        >
          {current ? (
            <>
              <form className="builder-form" onSubmit={handleAddSerial} style={{ marginTop: "12px" }}>
                <TextInput
                  label="Scan barcode"
                  ref={serialInputRef}
                  value={serial}
                  onChange={(e) => setSerial(e.target.value.toUpperCase())}
                  placeholder="Scan then press Enter"
                  autoFocus
                />
                <Button type="submit" disabled={isBusy || remaining <= 0}>
                  Add
                </Button>
              </form>
              <div style={{ marginTop: "12px" }}>
                <Button
                  variant="primary"
                  disabled={isBusy || remaining !== 0}
                  onClick={handleComplete}
                >
                  Complete pallet
                </Button>
              </div>
            </>
          ) : (
            <>
              <p style={{ marginBottom: "12px", color: "var(--color-text-secondary)" }}>
                Start a new pallet to begin scanning. Choose the customer, panel type, and pallet size you need.
              </p>
              <div style={{ display: "grid", gap: "8px", marginBottom: "8px" }}>
                <AnimatedSelect
                  label="Customer"
                  value={selectedCustomerId === "none" ? "" : String(selectedCustomerId)}
                  placeholder="No customer selected"
                  options={[
                    { value: "", label: "No customer selected" },
                    ...customers.map<AnimatedSelectOption>((customer) => ({
                      value: String(customer.id),
                      label: customer.display_name,
                    })),
                  ]}
                  onChange={(next) => {
                    if (!next) {
                      setSelectedCustomerId("none");
                    } else {
                      setSelectedCustomerId(Number(next));
                    }
                  }}
                  variant="pill"
                />
                <AnimatedSelect
                  label="Panel type"
                  value={newPalletTemplate}
                  options={TEMPLATE_OPTIONS.map<AnimatedSelectOption>((t) => ({
                    value: t,
                    label: t,
                  }))}
                  onChange={(next) => setNewPalletTemplate(next)}
                  variant="pill"
                />
                <AnimatedSelect
                  label="Pallet size"
                  value={String(newPalletSize)}
                  options={PALLET_SIZES.map<AnimatedSelectOption>((size) => ({
                    value: String(size),
                    label: `${size} panels`,
                  }))}
                  onChange={(next) => setNewPalletSize(Number(next))}
                  variant="pill"
                />
              </div>
              <Button type="button" disabled={isBusy} onClick={() => void handleStartNewPallet()}>
                Start new pallet
              </Button>
            </>
          )}
        </Card>

        {current && current.items.length > 0 ? (
          <Card title="Items on pallet">
            <ul className="flat-list">
              {current.items
                .slice()
                .sort((a, b) => a.slot_index - b.slot_index)
                .map((item) => (
                  <li key={item.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                    <span className="mono">{item.serial}</span>
                    <Button variant="danger" disabled={isBusy} onClick={() => void handleRemoveItem(item.id)}>
                      Remove
                    </Button>
                  </li>
                ))}
            </ul>
          </Card>
        ) : null}
      </section>
    </AppFrame>
  );
}
