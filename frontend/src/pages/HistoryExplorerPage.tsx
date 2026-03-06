import { FormEvent, useEffect, useMemo, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import AppFrame from "../components/layout/AppFrame";
import { useToast } from "../components/notifications/ToastProvider";
import AnimatedSelect from "../components/ui/AnimatedSelect";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import TextInput from "../components/ui/TextInput";
import { getPalletHistory, type AuditEvent } from "../features/audit";
import { searchBarcodes, type BarcodeSearchResult } from "../features/barcodes";
import { deletePallet } from "../features/pallets";
import { getExportDownloadUrl, listExportsByPallet, type ExportRecord } from "../features/exports";
import { listCustomers, type Customer } from "../features/customers";

export default function HistoryExplorerPage() {
  const { token } = useAuth();
  const { notify } = useToast();

  const [query, setQuery] = useState("");
  const [exact, setExact] = useState(false);
  const [datePreset, setDatePreset] = useState<"all" | "today" | "week" | "month" | "year">("all");
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [selectedCustomerId, setSelectedCustomerId] = useState<number | "all">("all");
  const [sortMode, setSortMode] = useState<"created_desc" | "created_asc" | "serial_asc" | "serial_desc" | "source">(
    "created_desc"
  );
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<BarcodeSearchResult[]>([]);
  const [selected, setSelected] = useState<BarcodeSearchResult | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [exports, setExports] = useState<ExportRecord[]>([]);

  const selectedPalletId = selected?.pallet_id ?? null;

  useEffect(() => {
    if (!token) return;
    void listCustomers(token, { isActive: true })
      .then((response) => {
        setCustomers(response.customers);
      })
      .catch(() => {
        // History still works without customer filter; swallow errors here.
      });
  }, [token]);

  const matchedSummary = useMemo(() => {
    if (!selected) {
      return "Select a result to view details.";
    }
    if (selected.source === "pallet_item") {
      return `Pallet #${selected.pallet_number ?? "-"} | Slot ${selected.slot_index ?? "-"}`;
    }
    return `Simulator batch ${selected.sim_batch_id ?? "-"} | ${selected.sim_result ?? "-"}`;
  }, [selected]);

  const sortToParams = () => {
    switch (sortMode) {
      case "created_asc":
        return { sort: "created_at" as const, order: "asc" as const };
      case "serial_asc":
        return { sort: "serial" as const, order: "asc" as const };
      case "serial_desc":
        return { sort: "serial" as const, order: "desc" as const };
      case "source":
        return { sort: "source" as const, order: "asc" as const };
      case "created_desc":
      default:
        return { sort: "created_at" as const, order: "desc" as const };
    }
  };

  const applyFilters = (rows: BarcodeSearchResult[]) => {
    let filtered = rows;

    // Date preset filter on created_at / sim_test_timestamp
    if (datePreset !== "all") {
      const now = new Date();
      let from: Date | null = null;
      switch (datePreset) {
        case "today": {
          const start = new Date(now);
          start.setHours(0, 0, 0, 0);
          from = start;
          break;
        }
        case "week": {
          const start = new Date(now);
          const day = start.getDay() || 7; // Monday as start of week
          start.setDate(start.getDate() - (day - 1));
          start.setHours(0, 0, 0, 0);
          from = start;
          break;
        }
        case "month": {
          const start = new Date(now.getFullYear(), now.getMonth(), 1);
          from = start;
          break;
        }
        case "year": {
          const start = new Date(now.getFullYear(), 0, 1);
          from = start;
          break;
        }
      }
      if (from) {
        filtered = filtered.filter((row) => {
          const raw =
            (row.created_at ? new Date(row.created_at) : null) ??
            (row.sim_test_timestamp ? new Date(row.sim_test_timestamp) : null);
          if (!raw || Number.isNaN(raw.getTime())) return false;
          return raw >= from;
        });
      }
    }

    // Customer filter for pallet-item rows
    if (selectedCustomerId !== "all") {
      filtered = filtered.filter((row) => {
        if (row.source !== "pallet_item") return false;
        return row.customer_id === selectedCustomerId;
      });
    }

    return filtered;
  };

  const runSearch = async (event: FormEvent) => {
    event.preventDefault();
    if (!token || !query.trim()) {
      return;
    }

    setIsLoading(true);
    try {
      const { sort, order } = sortToParams();
      const response = await searchBarcodes(token, {
        q: query.trim(),
        exact,
        limit: 100,
        sort,
        order,
      });
      setResults(response.results);
      setSelected(response.results[0] ?? null);
      setAuditEvents([]);
      setExports([]);
      if (response.total === 0) {
        notify("No matches found", "warning");
      } else {
        notify(`Found ${response.total} matches`, "success");
      }
    } catch {
      notify("Search failed", "error");
    } finally {
      setIsLoading(false);
    }
  };

  const loadDetails = async (row: BarcodeSearchResult) => {
    setSelected(row);
    setAuditEvents([]);
    setExports([]);

    if (!token || !row.pallet_id) {
      return;
    }

    try {
      const [historyRows, exportRows] = await Promise.all([
        getPalletHistory(token, row.pallet_id),
        listExportsByPallet(token, row.pallet_id),
      ]);
      setAuditEvents(historyRows);
      setExports(exportRows.exports);
    } catch {
      notify("Failed to load pallet details", "error");
    }
  };

  const handleOpenExport = async (exportId: number) => {
    if (!token) {
      return;
    }
    try {
      const response = await getExportDownloadUrl(token, exportId);
      window.open(response.download_url, "_blank", "noopener,noreferrer");
    } catch {
      notify("Failed to generate export URL", "error");
    }
  };

  const handleDeletePallet = async () => {
    if (!token || !selectedPalletId) {
      return;
    }
    const palletNumber = selected?.pallet_number;
    const confirmText =
      palletNumber != null
        ? `Delete pallet #${palletNumber}? This will free its serials for reuse but cannot be undone.`
        : "Delete this pallet? This will free its serials for reuse but cannot be undone.";
    if (!window.confirm(confirmText)) {
      return;
    }
    try {
      await deletePallet(token, selectedPalletId);
      setResults((prev) => prev.filter((row) => row.pallet_id !== selectedPalletId));
      setSelected(null);
      setAuditEvents([]);
      setExports([]);
      notify("Pallet deleted", "success");
    } catch {
      notify("Failed to delete pallet", "error");
    }
  };

  const visibleResults = useMemo(() => applyFilters(results), [results, datePreset, selectedCustomerId]);

  return (
    <AppFrame title="History Explorer">
      <section className="builder-grid">
        <Card title="Pallet History Filters">
          <form className="builder-form" onSubmit={runSearch}>
            <div className="builder-active-header">
              <AnimatedSelect
                label="Date"
                value={datePreset}
                onChange={(next) => setDatePreset(next as typeof datePreset)}
                variant="pill"
                className="builder-active-control builder-active-control--date"
                options={[
                  { value: "all", label: "All time" },
                  { value: "today", label: "Today" },
                  { value: "week", label: "This week" },
                  { value: "month", label: "This month" },
                  { value: "year", label: "This year" },
                ]}
              />
              <AnimatedSelect
                label="Customer"
                value={selectedCustomerId === "all" ? "" : String(selectedCustomerId)}
                placeholder="All customers"
                variant="pill"
                className="builder-active-control builder-active-control--customer"
                onChange={(value) => {
                  if (!value) {
                    setSelectedCustomerId("all");
                  } else {
                    setSelectedCustomerId(Number(value));
                  }
                }}
                options={[
                  { value: "", label: "All customers" },
                  ...customers.map((customer) => ({
                    value: String(customer.id),
                    label: customer.display_name,
                  })),
                ]}
              />
              <div style={{ display: "grid", gap: "6px", minWidth: "220px", flex: "1 1 220px" }}>
                <TextInput
                  label="Serial"
                  value={query}
                  onChange={(event) => setQuery(event.target.value.toUpperCase())}
                  placeholder="Enter full or partial serial"
                />
                <label className="ui-checkbox">
                  <input type="checkbox" checked={exact} onChange={(event) => setExact(event.target.checked)} />
                  Exact match only
                </label>
              </div>
              <AnimatedSelect
                label="Sort"
                value={sortMode}
                onChange={(next) => setSortMode(next as typeof sortMode)}
                variant="pill"
                className="builder-active-control builder-active-control--size"
                options={[
                  { value: "created_desc", label: "Newest activity first" },
                  { value: "created_asc", label: "Oldest activity first" },
                  { value: "serial_asc", label: "Serial A–Z" },
                  { value: "serial_desc", label: "Serial Z–A" },
                  { value: "source", label: "Source then serial" },
                ]}
              />
              <div style={{ display: "flex", alignItems: "flex-end", minWidth: "120px" }}>
                <Button type="submit" disabled={isLoading}>
                  {isLoading ? "Searching..." : "Search"}
                </Button>
              </div>
            </div>
          </form>
        </Card>
      </section>

      <section className="history-layout">
        <Card title="Results">
          {visibleResults.length === 0 ? (
            <p>No results yet.</p>
          ) : (
            <table className="items-table">
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Serial</th>
                  <th>Pallet</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {visibleResults.map((row, index) => (
                  <tr
                    key={`${row.source}-${row.serial}-${index}`}
                    className={selected === row ? "row-selected" : ""}
                    onClick={() => void loadDetails(row)}
                  >
                    <td>{row.source}</td>
                    <td className="mono">{row.serial}</td>
                    <td>{row.pallet_number ?? "-"}</td>
                    <td>{row.pallet_status ?? row.sim_result ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        <Card title="Details">
          <p>{matchedSummary}</p>

          {selectedPalletId ? (
            <>
              <div style={{ marginBottom: "8px" }}>
                <Button variant="danger" onClick={() => void handleDeletePallet()}>
                  Delete pallet
                </Button>
              </div>
              <h3 className="subhead">Exports</h3>
              {exports.length === 0 ? (
                <p>No exports found for this pallet.</p>
              ) : (
                <ul className="flat-list">
                  {exports.map((item) => (
                    <li key={item.id}>
                      <span>{item.file_name}</span>
                      <Button variant="secondary" onClick={() => void handleOpenExport(item.id)}>
                        Open
                      </Button>
                    </li>
                  ))}
                </ul>
              )}

              <h3 className="subhead">Audit Trail</h3>
              {auditEvents.length === 0 ? (
                <p>No audit events loaded.</p>
              ) : (
                <ul className="flat-list">
                  {auditEvents.slice(0, 12).map((event) => (
                    <li key={event.id}>
                      <span>{event.event_type}</span>
                      <small>{new Date(event.created_at).toLocaleString()}</small>
                    </li>
                  ))}
                </ul>
              )}
            </>
          ) : (
            <p>Select a pallet-item result to load pallet details and actions.</p>
          )}
        </Card>
      </section>
    </AppFrame>
  );
}
