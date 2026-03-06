import { FormEvent, useEffect, useRef, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import AppFrame from "../components/layout/AppFrame";
import { useToast } from "../components/notifications/ToastProvider";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import TextInput from "../components/ui/TextInput";
import { createExport, updatePallet, type Pallet } from "../features/pallets";
import {
  repoAddPalletItem,
  repoCompletePallet,
  repoCreatePallet,
  repoRemovePalletItem,
} from "../features/palletRepo";
import { getExportDownloadUrl } from "../features/exports";
import { listCustomers, type Customer } from "../features/customers";
import { ApiError } from "../lib/api";

const DEFAULT_MAX_PANELS = 25;
const TEMPLATE_OPTIONS = ["200WT", "220WT", "220M6", "330WT", "450WT", "450BT"];
const ACCESS_TOKEN_KEY = "pm2_access_token";
const PALLET_SIZES = [25, 26, 30, 35];
const CUSTOMERS_CACHE_KEY = "pm2_cached_customers";

type AnimatedSelectOption = {
  value: string;
  label: string;
};

type AnimatedSelectProps = {
  label: string;
  value: string;
  placeholder?: string;
  options: AnimatedSelectOption[];
  onChange: (value: string) => void;
  variant?: "default" | "pill";
};

function AnimatedSelect({
  label,
  value,
  placeholder,
  options,
  onChange,
  variant = "default",
}: AnimatedSelectProps) {
  const [isOpen, setIsOpen] = useState(false);

  const currentLabel =
    options.find((opt) => opt.value === value)?.label ?? (value ? value : placeholder ?? "Select...");

  const handleSelect = (nextValue: string) => {
    onChange(nextValue);
    setIsOpen(false);
  };

  return (
    <label
      className={
        variant === "pill"
          ? "ui-input-label animated-select animated-select--pill"
          : "ui-input-label animated-select"
      }
    >
      <span>{label}</span>
      <button
        type="button"
        className="animated-select__control"
        onClick={() => setIsOpen((open) => !open)}
      >
        <span className="animated-select__value">{currentLabel}</span>
        <span className="animated-select__caret">{isOpen ? "▲" : "▼"}</span>
      </button>
      <div
        className={
          isOpen
            ? "animated-select__options animated-select__options--open"
            : "animated-select__options"
        }
      >
        {options.map((opt) => (
          <button
            key={opt.value || opt.label}
            type="button"
            className="animated-select__option"
            onClick={() => handleSelect(opt.value)}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </label>
  );
}

function getEffectiveToken(contextToken: string | null): string | null {
  return contextToken ?? localStorage.getItem(ACCESS_TOKEN_KEY);
}

export default function LiveBuilderPage() {
  const { token: contextToken } = useAuth();
  const token = getEffectiveToken(contextToken);
  const { notify } = useToast();

  const [current, setCurrent] = useState<Pallet | null>(null);
  const [serial, setSerial] = useState("");
  const [isBusy, setIsBusy] = useState(false);
  const [newPalletTemplate, setNewPalletTemplate] = useState(TEMPLATE_OPTIONS[0]);
  const [newPalletSize, setNewPalletSize] = useState<number>(DEFAULT_MAX_PANELS);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [selectedCustomerId, setSelectedCustomerId] = useState<number | "none">("none");
  const [palletNumberDraft, setPalletNumberDraft] = useState<string>("");
  const [packoutDate, setPackoutDate] = useState<string>(() => {
    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, "0");
    const day = String(today.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  });
  const serialInputRef = useRef<HTMLInputElement | null>(null);

  const remaining = current ? current.max_panels - current.item_count : 0;

  useEffect(() => {
    if (current) {
      setPalletNumberDraft(String(current.pallet_number));
    } else {
      setPalletNumberDraft("");
    }
  }, [current]);

  useEffect(() => {
    // Start each app session with a clean Builder state instead of auto-resuming
    // previously active pallets from local cache/server.
    setCurrent(null);
  }, []);

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
      const created = await repoCreatePallet(token, {
        max_panels: newPalletSize,
        template_type: newPalletTemplate,
        customer_id: selectedCustomerId === "none" ? undefined : selectedCustomerId,
      });
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
      const updated = await repoAddPalletItem(token, current.id, s);
      setCurrent(updated);
      setSerial("");
      notify("Added", "success");
      serialInputRef.current?.focus();
    } catch (error) {
      if (error instanceof ApiError && error.errorCode === "SIM_DATA_REQUIRED") {
        const proceed = window.confirm(
          "No sun simulator data was found for this serial. Add anyway using generated in-range fallback values?"
        );
        if (proceed) {
          try {
            const updated = await repoAddPalletItem(token, current.id, s, { allowMissingSimData: true });
            setCurrent(updated);
            setSerial("");
            notify("Added with generated fallback simulator values", "warning");
            serialInputRef.current?.focus();
            return;
          } catch (retryError) {
            const retryMessage =
              retryError instanceof Error ? retryError.message : "Failed to add serial";
            notify(retryMessage, "error");
            return;
          }
        }
        notify("Serial not added", "warning");
        return;
      }
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
      const updated = await repoRemovePalletItem(token, current.id, itemId);
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
    const desiredTemplateType = newPalletTemplate;
    const desiredCustomerId = selectedCustomerId === "none" ? null : selectedCustomerId;
    const desiredMaxPanels = newPalletSize;
    const desiredPalletNumber = Number(palletNumberDraft);
    let workingPallet = current;
    const palletNumber = current.pallet_number;

    setIsBusy(true);
    try {
      if (
        token &&
        (
          workingPallet.template_type !== desiredTemplateType ||
          workingPallet.customer_id !== desiredCustomerId ||
          workingPallet.max_panels !== desiredMaxPanels ||
          (Number.isFinite(desiredPalletNumber) && desiredPalletNumber > 0 && workingPallet.pallet_number !== desiredPalletNumber)
        )
      ) {
        workingPallet = await updatePallet(token, workingPallet.id, {
          template_type: desiredTemplateType,
          customer_id: desiredCustomerId,
          max_panels: desiredMaxPanels,
          pallet_number: Number.isFinite(desiredPalletNumber) && desiredPalletNumber > 0 ? desiredPalletNumber : undefined,
        });
        setCurrent(workingPallet);
      } else if (
        !token &&
        (
          workingPallet.template_type !== desiredTemplateType ||
          workingPallet.customer_id !== desiredCustomerId ||
          workingPallet.max_panels !== desiredMaxPanels ||
          (Number.isFinite(desiredPalletNumber) && desiredPalletNumber > 0 && workingPallet.pallet_number !== desiredPalletNumber)
        )
      ) {
        workingPallet = {
          ...workingPallet,
          template_type: desiredTemplateType,
          customer_id: desiredCustomerId,
          max_panels: desiredMaxPanels,
          pallet_number:
            Number.isFinite(desiredPalletNumber) && desiredPalletNumber > 0
              ? desiredPalletNumber
              : workingPallet.pallet_number,
        };
        setCurrent(workingPallet);
      }

      const updated = await repoCompletePallet(token, workingPallet.id);
      setCurrent(updated);
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

  const commitPalletNumber = async () => {
    if (!current) return;
    const parsed = Number(palletNumberDraft);
    if (!Number.isInteger(parsed) || parsed <= 0) {
      setPalletNumberDraft(String(current.pallet_number));
      notify("Pallet number must be a positive whole number", "warning");
      return;
    }
    if (parsed === current.pallet_number) return;

    if (token) {
      try {
        const updated = await updatePallet(token, current.id, { pallet_number: parsed });
        setCurrent(updated);
        notify(`Pallet number updated to #${updated.pallet_number}`, "success");
      } catch (error) {
        const message = error instanceof Error ? error.message : "Failed to update pallet number";
        notify(message, "error");
        setPalletNumberDraft(String(current.pallet_number));
      }
      return;
    }

    setCurrent({ ...current, pallet_number: parsed });
    notify(`Pallet number updated to #${parsed} (offline pending sync)`, "warning");
  };

  return (
    <AppFrame title="Builder">
      {current ? (
        <section className="builder-active-header">
          <label className="builder-active-pill builder-active-pill--input">
            <span className="builder-active-pill__label">Pallet</span>
            <input
              className="builder-active-pill__number"
              type="number"
              min={1}
              value={palletNumberDraft}
              onChange={(event) => setPalletNumberDraft(event.target.value)}
              onBlur={() => void commitPalletNumber()}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  void commitPalletNumber();
                }
              }}
            />
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
          />
          <AnimatedSelect
            label="Pallet Size"
            value={String(newPalletSize)}
            options={PALLET_SIZES.map<AnimatedSelectOption>((size) => ({
              value: String(size),
              label: `${size} panels`,
            }))}
            onChange={(next) => setNewPalletSize(Number(next))}
            variant="pill"
          />
          <label className="builder-active-pill builder-active-pill--input">
            <span className="builder-active-pill__label">Packout date</span>
            <input
              className="builder-active-pill__date"
              type="date"
              value={packoutDate}
              onChange={(event) => setPackoutDate(event.target.value)}
            />
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
                  label="Customer (optional)"
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
                />
                <AnimatedSelect
                  label="Panel type"
                  value={newPalletTemplate}
                  options={TEMPLATE_OPTIONS.map<AnimatedSelectOption>((t) => ({
                    value: t,
                    label: t,
                  }))}
                  onChange={(next) => setNewPalletTemplate(next)}
                />
                <AnimatedSelect
                  label="Pallet size"
                  value={String(newPalletSize)}
                  options={PALLET_SIZES.map<AnimatedSelectOption>((size) => ({
                    value: String(size),
                    label: `${size} panels`,
                  }))}
                  onChange={(next) => setNewPalletSize(Number(next))}
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
