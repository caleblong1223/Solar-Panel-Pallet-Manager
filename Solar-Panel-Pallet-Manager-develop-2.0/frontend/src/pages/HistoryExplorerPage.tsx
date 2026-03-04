import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import AppFrame from "../components/layout/AppFrame";
import { useToast } from "../components/notifications/ToastProvider";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import TextInput from "../components/ui/TextInput";
import { getPalletHistory, type AuditEvent } from "../features/audit";
import { searchBarcodes, type BarcodeSearchResult } from "../features/barcodes";
import { getExportDownloadUrl, listExportsByPallet, type ExportRecord } from "../features/exports";
import { createExport, deletePallet, searchPallets, type Pallet } from "../features/pallets";
import { listCustomers, type Customer } from "../features/customers";

export default function HistoryExplorerPage() {
  const { token } = useAuth();
  const { notify } = useToast();

  const [query, setQuery] = useState("");
  const [exact, setExact] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<BarcodeSearchResult[]>([]);
  const [selected, setSelected] = useState<BarcodeSearchResult | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [exports, setExports] = useState<ExportRecord[]>([]);

  const [pallets, setPallets] = useState<Pallet[]>([]);
  const [selectedPallet, setSelectedPallet] = useState<Pallet | null>(null);
  const [selectedPalletIds, setSelectedPalletIds] = useState<Set<number>>(new Set());
  const [palletAuditEvents, setPalletAuditEvents] = useState<AuditEvent[]>([]);
  const [palletExports, setPalletExports] = useState<ExportRecord[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [palletStatusFilter, setPalletStatusFilter] = useState<string>("completed");
  const [palletCustomerFilter, setPalletCustomerFilter] = useState<string>("");
  const [palletDatePreset, setPalletDatePreset] = useState<string>("this_month");
  const [bulkTemplate, setBulkTemplate] = useState<string>("200WT");
  const searchDebounceRef = useRef<number | null>(null);
  const [serialSort, setSerialSort] = useState<"created_at" | "serial" | "source">("created_at");
  const [serialOrder, setSerialOrder] = useState<"asc" | "desc">("desc");
  const [palletSortKey, setPalletSortKey] = useState<"pallet_number" | "created_at" | "completed_at">("created_at");
  const [palletSortDir, setPalletSortDir] = useState<"asc" | "desc">("desc");

  const selectedPalletId = selected?.pallet_id ?? null;

  const matchedSummary = useMemo(() => {
    if (!selected) {
      return "Select a result to view details.";
    }
    if (selected.source === "pallet_item") {
      return `Pallet #${selected.pallet_number ?? "-"} | Slot ${selected.slot_index ?? "-"}`;
    }
    return `Simulator batch ${selected.sim_batch_id ?? "-"} | ${selected.sim_result ?? "-"}`;
  }, [selected]);

  const runSearch = async () => {
    if (!token || !query.trim()) {
      return;
    }

    setIsLoading(true);
    try {
      const response = await searchBarcodes(token, {
        q: query.trim(),
        exact,
        limit: 100,
        sort: serialSort,
        order: serialOrder,
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

  const handleSearchSubmit = (event: FormEvent) => {
    event.preventDefault();
    void runSearch();
  };

  useEffect(() => {
    if (!token || !query.trim()) {
      return;
    }
    if (searchDebounceRef.current !== null) {
      window.clearTimeout(searchDebounceRef.current);
    }
    searchDebounceRef.current = window.setTimeout(() => {
      void runSearch();
    }, 300);
    return () => {
      if (searchDebounceRef.current !== null) {
        window.clearTimeout(searchDebounceRef.current);
      }
    };
  }, [query, exact, token, serialSort, serialOrder]);

  const sortedPallets = useMemo(() => {
    const copy = [...pallets];
    copy.sort((a, b) => {
      let aVal: number | string | Date | null = null;
      let bVal: number | string | Date | null = null;
      if (palletSortKey === "pallet_number") {
        aVal = a.pallet_number;
        bVal = b.pallet_number;
      } else if (palletSortKey === "created_at") {
        aVal = new Date(a.created_at);
        bVal = new Date(b.created_at);
      } else {
        aVal = a.completed_at ? new Date(a.completed_at) : new Date(0);
        bVal = b.completed_at ? new Date(b.completed_at) : new Date(0);
      }
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return palletSortDir === "asc" ? -1 : 1;
      if (bVal == null) return palletSortDir === "asc" ? 1 : -1;
      if (aVal < bVal) return palletSortDir === "asc" ? -1 : 1;
      if (aVal > bVal) return palletSortDir === "asc" ? 1 : -1;
      return 0;
    });
    return copy;
  }, [pallets, palletSortKey, palletSortDir]);

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
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to generate export URL";
      // Special-case missing objects to act like 1.1's ghost-pallet protection.
      if (message.toLowerCase().includes("not found") || message.toLowerCase().includes("nosuchkey")) {
        notify("Export file is missing from storage. This record may refer to a removed artifact.", "warning");
      } else {
        notify(message, "error");
      }
    }
  };

  const handleBulkExportSelectedPallets = async () => {
    if (!token || selectedPalletIds.size === 0) {
      return;
    }
    setIsLoading(true);
    try {
      let successCount = 0;
      let failureCount = 0;
      for (const id of selectedPalletIds) {
        try {
          await createExport(token, { pallet_id: id, template_type: bulkTemplate });
          successCount += 1;
        } catch (error) {
          failureCount += 1;
          const message = error instanceof Error ? error.message : "Failed to create export";
          notify(`Pallet ${id}: ${message}`, "error");
        }
      }
      if (successCount > 0) {
        notify(`Created exports for ${successCount} pallet(s)`, "success");
        if (selectedPallet) {
          try {
            const response = await listExportsByPallet(token, selectedPallet.id);
            setPalletExports(response.exports);
          } catch {
            // ignore
          }
        }
      }
      if (failureCount === 0 && successCount === 0) {
        notify("No exports were created", "warning");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteSelectedPallets = async () => {
    if (!token || selectedPalletIds.size === 0) {
      return;
    }
    const confirmed = window.confirm(
      `Delete ${selectedPalletIds.size} pallet(s)? This will mark them as deleted and hide them from normal views.`
    );
    if (!confirmed) {
      return;
    }
    setIsLoading(true);
    try {
      for (const id of selectedPalletIds) {
        try {
          await deletePallet(token, id);
        } catch (error) {
          const message = error instanceof Error ? error.message : "Failed to delete pallet";
          notify(`Pallet ${id}: ${message}`, "error");
        }
      }
      notify("Delete operation completed", "success");
      setSelectedPalletIds(new Set());
      await loadPallets();
      setSelectedPallet(null);
      setPalletAuditEvents([]);
      setPalletExports([]);
    } finally {
      setIsLoading(false);
    }
  };

  const computeDateRange = () => {
    const now = new Date();
    const start = new Date(now);

    switch (palletDatePreset) {
      case "today":
        start.setHours(0, 0, 0, 0);
        return { from: start.toISOString(), to: now.toISOString() };
      case "this_week": {
        const day = now.getDay() || 7;
        start.setDate(now.getDate() - (day - 1));
        start.setHours(0, 0, 0, 0);
        return { from: start.toISOString(), to: now.toISOString() };
      }
      case "this_year":
        start.setMonth(0, 1);
        start.setHours(0, 0, 0, 0);
        return { from: start.toISOString(), to: now.toISOString() };
      case "this_month":
        start.setDate(1);
        start.setHours(0, 0, 0, 0);
        return { from: start.toISOString(), to: now.toISOString() };
      case "all":
      default:
        return { from: undefined, to: undefined };
    }
  };

  const loadPallets = async (event?: FormEvent) => {
    event?.preventDefault();
    if (!token) {
      return;
    }

    setIsLoading(true);
    try {
      const dateRange = computeDateRange();
      const status = palletStatusFilter || undefined;
      const customerId =
        palletCustomerFilter && Number.isFinite(Number.parseInt(palletCustomerFilter, 10))
          ? Number.parseInt(palletCustomerFilter, 10)
          : undefined;

      const response = await searchPallets(token, {
        status,
        customer_id: customerId,
        completed_from: status === "completed" ? dateRange.from : undefined,
        completed_to: status === "completed" ? dateRange.to : undefined,
        created_from: status && status !== "completed" ? dateRange.from : undefined,
        created_to: status && status !== "completed" ? dateRange.to : undefined,
      });
      setPallets(response.pallets);
      setSelectedPallet(response.pallets[0] ?? null);
      setPalletAuditEvents([]);
      setPalletExports([]);
      notify(`Loaded ${response.total} pallets`, "success");
    } catch {
      notify("Failed to load pallets", "error");
    } finally {
      setIsLoading(false);
    }
  };

  const loadPalletDetails = async (pallet: Pallet) => {
    setSelectedPallet(pallet);
    setPalletAuditEvents([]);
    setPalletExports([]);
    if (!token) {
      return;
    }
    try {
      const [historyRows, exportRows] = await Promise.all([
        getPalletHistory(token, pallet.id),
        listExportsByPallet(token, pallet.id),
      ]);
      setPalletAuditEvents(historyRows);
      setPalletExports(exportRows.exports);
    } catch {
      notify("Failed to load pallet details", "error");
    }
  };

  const selectedPalletCustomerName =
    selectedPallet && selectedPallet.customer_id
      ? customers.find((c) => c.id === selectedPallet.customer_id)?.display_name ?? `#${selectedPallet.customer_id}`
      : "-";

  // Load customers once for filters and labels
  if (token && customers.length === 0) {
    void (async () => {
      try {
        const response = await listCustomers(token, true);
        setCustomers(response.customers);
      } catch {
        // ignore; history still works without customers
      }
    })();
  }

  return (
    <AppFrame title="History Explorer">
      <section className="builder-grid">
        <Card title="Search by serial">
          <form className="builder-form" onSubmit={handleSearchSubmit}>
            <TextInput
              label="Serial query"
              value={query}
              onChange={(event) => setQuery(event.target.value.toUpperCase())}
              placeholder="Enter full or partial serial"
              required
            />
            <label className="ui-checkbox">
              <input type="checkbox" checked={exact} onChange={(event) => setExact(event.target.checked)} />
              Exact match only
            </label>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? "Searching..." : "Search"}
            </Button>
          </form>
        </Card>
      </section>

      <section className="history-layout">
        <Card title="Results">
          {results.length === 0 ? (
            <p>No results yet. Enter a serial above to search pallets and simulator data.</p>
          ) : (
            <table className="items-table">
              <thead>
                <tr>
                  <th
                    role="button"
                    onClick={() =>
                      setSerialSort((prev) => {
                        const nextKey: "source" | "serial" = "source";
                        if (prev === nextKey) {
                          setSerialOrder((d) => (d === "asc" ? "desc" : "asc"));
                          return prev;
                        }
                        setSerialOrder("asc");
                        return nextKey;
                      })
                    }
                  >
                    Source {serialSort === "source" ? (serialOrder === "asc" ? "▲" : "▼") : ""}
                  </th>
                  <th
                    role="button"
                    onClick={() =>
                      setSerialSort((prev) => {
                        const nextKey: "serial" = "serial";
                        if (prev === nextKey) {
                          setSerialOrder((d) => (d === "asc" ? "desc" : "asc"));
                          return prev;
                        }
                        setSerialOrder("asc");
                        return nextKey;
                      })
                    }
                  >
                    Serial {serialSort === "serial" ? (serialOrder === "asc" ? "▲" : "▼") : ""}
                  </th>
                  <th>Pallet</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {results.map((row, index) => (
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

      <section className="builder-grid">
        <Card title="Pallet history filters">
          <form className="builder-form" onSubmit={loadPallets}>
            <label className="ui-input-label">
              <span>Status</span>
              <select
                className="ui-select"
                value={palletStatusFilter}
                onChange={(event) => setPalletStatusFilter(event.target.value)}
              >
                <option value="">All</option>
                <option value="active">Active</option>
                <option value="completed">Completed</option>
              </select>
            </label>

            <label className="ui-input-label">
              <span>Customer</span>
              <select
                className="ui-select"
                value={palletCustomerFilter}
                onChange={(event) => setPalletCustomerFilter(event.target.value)}
              >
                <option value="">All customers</option>
                {customers.map((customer) => (
                  <option key={customer.id} value={customer.id}>
                    {customer.display_name}
                  </option>
                ))}
              </select>
            </label>

            <label className="ui-input-label">
              <span>Date range</span>
              <select
                className="ui-select"
                value={palletDatePreset}
                onChange={(event) => setPalletDatePreset(event.target.value)}
              >
                <option value="all">All time</option>
                <option value="today">Today</option>
                <option value="this_week">This week</option>
                <option value="this_month">This month</option>
                <option value="this_year">This year</option>
              </select>
            </label>

            <label className="ui-input-label">
              <span>Export template for bulk actions</span>
              <select
                className="ui-select"
                value={bulkTemplate}
                onChange={(event) => setBulkTemplate(event.target.value)}
              >
                <option value="200WT">200WT</option>
                <option value="220WT">220WT</option>
                <option value="220M6">220M6</option>
                <option value="330WT">330WT</option>
                <option value="450WT">450WT</option>
                <option value="450BT">450BT</option>
              </select>
            </label>

            <Button type="submit" disabled={isLoading}>
              {isLoading ? "Loading..." : "Load pallets"}
            </Button>
          </form>
        </Card>
      </section>

      <section className="history-layout">
        <Card title="Pallets">
          {pallets.length === 0 ? (
            <p>No pallets loaded yet. Adjust filters above and click “Load pallets”.</p>
          ) : (
            <>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: 12,
                  marginBottom: 8,
                  flexWrap: "wrap",
                }}
              >
                <small>
                  Selected: {selectedPalletIds.size} / {pallets.length}
                </small>
                <div style={{ display: "flex", gap: 8 }}>
                  <Button
                    variant="secondary"
                    disabled={isLoading || selectedPalletIds.size === 0}
                    onClick={() => void handleBulkExportSelectedPallets()}
                  >
                    Create Exports
                  </Button>
                  <Button
                    variant="danger"
                    disabled={isLoading || selectedPalletIds.size === 0}
                    onClick={() => void handleDeleteSelectedPallets()}
                  >
                    Delete Selected
                  </Button>
                </div>
              </div>
            <table className="items-table">
              <thead>
                <tr>
                  <th>
                    <input
                      type="checkbox"
                      aria-label="Select all pallets"
                      checked={selectedPalletIds.size > 0 && selectedPalletIds.size === pallets.length}
                      onChange={(event) => {
                        if (event.target.checked) {
                          setSelectedPalletIds(new Set(pallets.map((pallet) => pallet.id)));
                        } else {
                          setSelectedPalletIds(new Set());
                        }
                      }}
                    />
                  </th>
                  <th
                    role="button"
                    onClick={() => {
                      setPalletSortKey((prev) => {
                        const next = "pallet_number" as const;
                        if (prev === next) {
                          setPalletSortDir((d) => (d === "asc" ? "desc" : "asc"));
                          return prev;
                        }
                        setPalletSortDir("asc");
                        return next;
                      });
                    }}
                  >
                    #
                    {palletSortKey === "pallet_number" ? (palletSortDir === "asc" ? " ▲" : " ▼") : ""}
                  </th>
                  <th>Status</th>
                  <th>Customer</th>
                  <th
                    role="button"
                    onClick={() => {
                      setPalletSortKey((prev) => {
                        const next = "created_at" as const;
                        if (prev === next) {
                          setPalletSortDir((d) => (d === "asc" ? "desc" : "asc"));
                          return prev;
                        }
                        setPalletSortDir("asc");
                        return next;
                      });
                    }}
                  >
                    Created
                    {palletSortKey === "created_at" ? (palletSortDir === "asc" ? " ▲" : " ▼") : ""}
                  </th>
                  <th
                    role="button"
                    onClick={() => {
                      setPalletSortKey((prev) => {
                        const next = "completed_at" as const;
                        if (prev === next) {
                          setPalletSortDir((d) => (d === "asc" ? "desc" : "asc"));
                          return prev;
                        }
                        setPalletSortDir("asc");
                        return next;
                      });
                    }}
                  >
                    Completed
                    {palletSortKey === "completed_at" ? (palletSortDir === "asc" ? " ▲" : " ▼") : ""}
                  </th>
                  <th>Count</th>
                </tr>
              </thead>
              <tbody>
                {sortedPallets.map((pallet) => {
                  const isRowSelected = selectedPallet?.id === pallet.id;
                  const isChecked = selectedPalletIds.has(pallet.id);
                  return (
                  <tr
                    key={pallet.id}
                    className={isRowSelected ? "row-selected" : ""}
                    onClick={() => void loadPalletDetails(pallet)}
                  >
                    <td>
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={(event) => {
                          event.stopPropagation();
                          setSelectedPalletIds((prev) => {
                            const next = new Set(prev);
                            if (event.target.checked) {
                              next.add(pallet.id);
                            } else {
                              next.delete(pallet.id);
                            }
                            return next;
                          });
                        }}
                      />
                    </td>
                    <td>{pallet.pallet_number}</td>
                    <td>{pallet.status}</td>
                    <td>
                      {pallet.customer_id
                        ? customers.find((c) => c.id === pallet.customer_id)?.display_name ?? `#${pallet.customer_id}`
                        : "-"}
                    </td>
                    <td>{new Date(pallet.created_at).toLocaleString()}</td>
                    <td>{pallet.completed_at ? new Date(pallet.completed_at).toLocaleString() : "-"}</td>
                    <td>
                      {pallet.item_count}/{pallet.max_panels}
                    </td>
                  </tr>
                );})}
              </tbody>
            </table>
            </>
          )}
        </Card>

        <Card title="Pallet details">
          {selectedPallet ? (
            <>
              <p>
                Pallet #{selectedPallet.pallet_number} · Status {selectedPallet.status}
              </p>
              <p>Customer: {selectedPalletCustomerName}</p>
              <p>
                Panels: {selectedPallet.item_count}/{selectedPallet.max_panels}
              </p>

              <h3 className="subhead">Exports</h3>
              {palletExports.length === 0 ? (
                <p>No exports found for this pallet.</p>
              ) : (
                <ul className="flat-list">
                  {palletExports.map((item) => (
                    <li key={item.id}>
                      <span>{item.file_name}</span>
                      <Button variant="secondary" onClick={() => void handleOpenExport(item.id)}>
                        Open
                      </Button>
                    </li>
                  ))}
                </ul>
              )}

              <h3 className="subhead">Audit trail</h3>
              {palletAuditEvents.length === 0 ? (
                <p>No audit events loaded.</p>
              ) : (
                <ul className="flat-list">
                  {palletAuditEvents.slice(0, 12).map((event) => (
                    <li key={event.id}>
                      <span>{event.event_type}</span>
                      <small>{new Date(event.created_at).toLocaleString()}</small>
                    </li>
                  ))}
                </ul>
              )}
            </>
          ) : (
            <p>Select a pallet from the table to load details.</p>
          )}
        </Card>
      </section>
    </AppFrame>
  );
}
