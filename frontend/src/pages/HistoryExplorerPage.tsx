import { FormEvent, useEffect, useMemo, useState } from "react";
import Spreadsheet from "react-spreadsheet";
import type { CellBase, Matrix } from "react-spreadsheet";
import * as XLSX from "xlsx";
import { useAuth } from "../auth/AuthContext";
import AppFrame from "../components/layout/AppFrame";
import { useToast } from "../components/notifications/ToastProvider";
import AnimatedSelect from "../components/ui/AnimatedSelect";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import TextInput from "../components/ui/TextInput";
import { deletePallet, getPallet, listPallets, type Pallet } from "../features/pallets";
import {
  downloadExportWorkbook,
  getExportDownloadEndpoint,
  listExportsByPallet,
  replaceExportWorkbook,
  type ExportRecord,
} from "../features/exports";
import { listCustomers, type Customer } from "../features/customers";

type SheetCell = CellBase<string>;
type EditableSheet = {
  name: string;
  data: Matrix<SheetCell>;
};

function matrixFromRows(rows: unknown[][]): Matrix<SheetCell> {
  const normalizedRows = rows.length > 0 ? rows : [[""]];
  return normalizedRows.map((row) => {
    const normalizedCols = row.length > 0 ? row : [""];
    return normalizedCols.map((value) => ({
      value: value == null ? "" : String(value),
    }));
  });
}

export default function HistoryExplorerPage() {
  const { token } = useAuth();
  const { notify } = useToast();
  const apiToken = token ?? "";

  const [query, setQuery] = useState("");
  const [exact, setExact] = useState(false);
  const [datePreset, setDatePreset] = useState<"all" | "today" | "week" | "month" | "year">("today");
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [selectedCustomerId, setSelectedCustomerId] = useState<number | "all">("all");
  const [sortMode, setSortMode] = useState<"completed_desc" | "completed_asc" | "number_desc" | "number_asc" | "items_desc">(
    "completed_desc"
  );
  const [isLoading, setIsLoading] = useState(false);
  const [pallets, setPallets] = useState<Pallet[]>([]);
  const [selectedPalletId, setSelectedPalletId] = useState<number | null>(null);
  const [exports, setExports] = useState<ExportRecord[]>([]);
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [isEditorLoading, setIsEditorLoading] = useState(false);
  const [isSavingEdit, setIsSavingEdit] = useState(false);
  const [editingExport, setEditingExport] = useState<ExportRecord | null>(null);
  const [editableSheets, setEditableSheets] = useState<EditableSheet[]>([]);
  const [activeSheetIndex, setActiveSheetIndex] = useState(0);

  const selectedPallet = useMemo(
    () => pallets.find((pallet) => pallet.id === selectedPalletId) ?? null,
    [pallets, selectedPalletId]
  );

  useEffect(() => {
    void listCustomers(apiToken, { isActive: true })
      .then((response) => {
        setCustomers(response.customers);
      })
      .catch(() => {
        // History still works without customer filter; swallow errors here.
      });
  }, [apiToken]);

  const loadHistory = async () => {
    setIsLoading(true);
    try {
      let response = await listPallets(apiToken, "completed", { timeoutMs: 10000 });
      if (response.total === 0) {
        // Some deployments keep historical pallets in non-completed states.
        response = await listPallets(apiToken, "active", { timeoutMs: 10000 });
      }
      setPallets(response.pallets);
      setSelectedPalletId((previous) => {
        if (previous && response.pallets.some((pallet) => pallet.id === previous)) {
          return previous;
        }
        return response.pallets[0]?.id ?? null;
      });
      if (response.total === 0) {
        notify("No history records found", "warning");
      }
      return response.pallets;
    } catch {
      // Retry once after short delay to handle bundled backend warm-up.
      await new Promise((resolve) => window.setTimeout(resolve, 800));
      try {
        const retry = await listPallets(apiToken, "completed", { timeoutMs: 10000 });
        setPallets(retry.pallets);
        setSelectedPalletId((previous) => {
          if (previous && retry.pallets.some((pallet) => pallet.id === previous)) {
            return previous;
          }
          return retry.pallets[0]?.id ?? null;
        });
        if (retry.total === 0) {
          notify("No history records found", "warning");
        }
        return retry.pallets;
      } catch {
        notify("Failed to load history", "error");
      }
      return [];
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadHistory();
  }, [apiToken]);

  const matchedSummary = useMemo(() => {
    if (!selectedPallet) {
      return "Select a pallet to view details.";
    }
    return `Pallet #${selectedPallet.pallet_number} | ${selectedPallet.template_type ?? "Unknown type"} | ${selectedPallet.item_count} panel${selectedPallet.item_count === 1 ? "" : "s"}`;
  }, [selectedPallet]);

  const applyFilters = (rows: Pallet[]) => {
    let filtered = [...rows];

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
        filtered = filtered.filter((pallet) => {
          const raw = pallet.completed_at ? new Date(pallet.completed_at) : new Date(pallet.created_at);
          if (!raw || Number.isNaN(raw.getTime())) return false;
          return raw >= from;
        });
      }
    }

    // Customer filter for pallet-item rows
    if (selectedCustomerId !== "all") {
      filtered = filtered.filter((pallet) => pallet.customer_id === selectedCustomerId);
    }

    const normalizedQuery = query.trim().toUpperCase();
    if (normalizedQuery) {
      filtered = filtered.filter((pallet) => {
        const panelType = (pallet.template_type ?? "").toUpperCase();
        const palletNumber = String(pallet.pallet_number);
        if (exact) {
          return (
            pallet.items.some((item) => item.serial.toUpperCase() === normalizedQuery) ||
            palletNumber === normalizedQuery ||
            panelType === normalizedQuery
          );
        }
        return (
          pallet.items.some((item) => item.serial.toUpperCase().includes(normalizedQuery)) ||
          palletNumber.includes(normalizedQuery) ||
          panelType.includes(normalizedQuery)
        );
      });
    }

    switch (sortMode) {
      case "completed_asc":
        filtered.sort((a, b) => {
          const aTime = new Date(a.completed_at ?? a.created_at).getTime();
          const bTime = new Date(b.completed_at ?? b.created_at).getTime();
          return aTime - bTime;
        });
        break;
      case "number_asc":
        filtered.sort((a, b) => a.pallet_number - b.pallet_number);
        break;
      case "number_desc":
        filtered.sort((a, b) => b.pallet_number - a.pallet_number);
        break;
      case "items_desc":
        filtered.sort((a, b) => b.item_count - a.item_count);
        break;
      case "completed_desc":
      default:
        filtered.sort((a, b) => {
          const aTime = new Date(a.completed_at ?? a.created_at).getTime();
          const bTime = new Date(b.completed_at ?? b.created_at).getTime();
          return bTime - aTime;
        });
        break;
    }

    return filtered;
  };

  const runSearch = async (event: FormEvent) => {
    event.preventDefault();
    const latest = await loadHistory();
    const visible = applyFilters(latest);
    if (visible.length === 0) {
      notify("No matching pallets found", "warning");
    } else {
      notify(`Showing ${visible.length} pallet${visible.length === 1 ? "" : "s"}`, "success");
    }
  };

  const loadDetails = async (palletId: number) => {
    setSelectedPalletId(palletId);
    setExports([]);

    try {
      const [palletRow, exportRows] = await Promise.all([
        getPallet(apiToken, palletId),
        listExportsByPallet(apiToken, palletId),
      ]);
      setPallets((previous) =>
        previous.map((entry) => (entry.id === palletId ? palletRow : entry))
      );
      setExports(exportRows.exports);
    } catch {
      notify("Failed to load pallet details", "error");
    }
  };

  const handleOpenExport = (exportId: number, format: "pdf" | "xlsx") => {
    const endpoint = getExportDownloadEndpoint(exportId, format);
    window.open(endpoint, "_blank", "noopener,noreferrer");
  };

  const handleDeletePallet = async () => {
    if (!selectedPalletId) {
      return;
    }
    const palletNumber = selectedPallet?.pallet_number;
    const confirmText =
      palletNumber != null
        ? `Delete pallet #${palletNumber}? This will free its serials for reuse but cannot be undone.`
        : "Delete this pallet? This will free its serials for reuse but cannot be undone.";
    if (!window.confirm(confirmText)) {
      return;
    }
    try {
      await deletePallet(apiToken, selectedPalletId);
      setPallets((prev) => prev.filter((row) => row.id !== selectedPalletId));
      setSelectedPalletId(null);
      setExports([]);
      notify("Pallet deleted", "success");
    } catch {
      notify("Failed to delete pallet", "error");
    }
  };

  const closeEditor = () => {
    setIsEditorOpen(false);
    setIsEditorLoading(false);
    setIsSavingEdit(false);
    setEditingExport(null);
    setEditableSheets([]);
    setActiveSheetIndex(0);
  };

  const refreshPalletExports = async (palletId: number) => {
    const exportRows = await listExportsByPallet(apiToken, palletId);
    setExports(exportRows.exports);
  };

  const handleEditExport = async (item: ExportRecord) => {
    setIsEditorOpen(true);
    setIsEditorLoading(true);
    setEditingExport(item);
    setEditableSheets([]);
    setActiveSheetIndex(0);
    try {
      const workbookBuffer = await downloadExportWorkbook(apiToken, item.id);
      const workbook = XLSX.read(workbookBuffer, { type: "array" });
      const sheetNames = workbook.SheetNames;
      if (sheetNames.length === 0) {
        throw new Error("Workbook contains no sheets");
      }
      const nextSheets: EditableSheet[] = sheetNames.map((name) => {
        const worksheet = workbook.Sheets[name];
        const rows = XLSX.utils.sheet_to_json(worksheet, {
          header: 1,
          raw: false,
          blankrows: true,
          defval: "",
        }) as unknown[][];
        return {
          name,
          data: matrixFromRows(rows),
        };
      });
      setEditableSheets(nextSheets);
    } catch (error) {
      closeEditor();
      const message = error instanceof Error ? error.message : "Failed to load export workbook for editing";
      notify(message, "error");
    } finally {
      setIsEditorLoading(false);
    }
  };

  const handleSheetDataChange = (nextData: Matrix<SheetCell>) => {
    setEditableSheets((prev) =>
      prev.map((sheet, index) => (index === activeSheetIndex ? { ...sheet, data: nextData } : sheet))
    );
  };

  const handleSaveSpreadsheet = async () => {
    if (!editingExport || editableSheets.length === 0) {
      return;
    }
    setIsSavingEdit(true);
    try {
      const workbook = XLSX.utils.book_new();
      editableSheets.forEach((sheet) => {
        const rowData = sheet.data.map((row) => row.map((cell) => cell?.value ?? ""));
        const worksheet = XLSX.utils.aoa_to_sheet(rowData.length > 0 ? rowData : [[""]]);
        XLSX.utils.book_append_sheet(workbook, worksheet, sheet.name);
      });
      const workbookBytes = XLSX.write(workbook, { type: "array", bookType: "xlsx" });
      const blob = new Blob([workbookBytes], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      });
      const baseName = editingExport.file_name.toLowerCase().endsWith(".pdf")
        ? editingExport.file_name.slice(0, -4)
        : editingExport.file_name;
      const fileName = baseName.toLowerCase().endsWith(".xlsx") ? baseName : `${baseName}.xlsx`;
      await replaceExportWorkbook(apiToken, editingExport.id, blob, fileName);
      if (selectedPalletId) {
        await refreshPalletExports(selectedPalletId);
      }
      closeEditor();
      notify("Spreadsheet changes saved", "success");
    } catch {
      notify("Failed to save spreadsheet changes", "error");
    } finally {
      setIsSavingEdit(false);
    }
  };

  const visiblePallets = useMemo(
    () => applyFilters(pallets),
    [pallets, datePreset, selectedCustomerId, query, exact, sortMode]
  );

  return (
    <AppFrame title="History Explorer">
      <section className="builder-grid">
        <Card title="Pallet History Filters" className="history-filters-card">
          <form className="builder-form" onSubmit={runSearch}>
            <div className="history-filter-grid">
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
              <AnimatedSelect
                label="Sort"
                value={sortMode}
                onChange={(next) => setSortMode(next as typeof sortMode)}
                variant="pill"
                className="builder-active-control builder-active-control--size"
                options={[
                  { value: "completed_desc", label: "Newest packout first" },
                  { value: "completed_asc", label: "Oldest packout first" },
                  { value: "number_asc", label: "Pallet number low-high" },
                  { value: "number_desc", label: "Pallet number high-low" },
                  { value: "items_desc", label: "Most panels first" },
                ]}
              />
              <div className="history-button-wrapper">
                <Button type="submit" disabled={isLoading}>
                  {isLoading ? "Refreshing..." : "Search"}
                </Button>
              </div>
            </div>
            <div style={{ display: "grid", gap: "6px" }}>
              <TextInput
                label="Serial / Pallet / Panel Type"
                value={query}
                onChange={(event) => setQuery(event.target.value.toUpperCase())}
                placeholder="Filter completed pallets"
              />
              <label className="ui-checkbox">
                <input type="checkbox" checked={exact} onChange={(event) => setExact(event.target.checked)} />
                Exact match only
              </label>
            </div>
          </form>
        </Card>
      </section>

      <section className="history-layout">
        <Card title="Results">
          {visiblePallets.length === 0 ? (
            <p>No pallets found.</p>
          ) : (
            <table className="items-table">
              <thead>
                <tr>
                  <th>Pallet</th>
                  <th>Panel Type</th>
                  <th>Panels</th>
                  <th>Packout Date</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {visiblePallets.map((row) => (
                  <tr
                    key={row.id}
                    className={selectedPalletId === row.id ? "row-selected" : ""}
                    onClick={() => void loadDetails(row.id)}
                  >
                    <td>{row.pallet_number}</td>
                    <td>{row.template_type ?? "-"}</td>
                    <td>{row.item_count}</td>
                    <td>{row.completed_at ? new Date(row.completed_at).toLocaleDateString() : "-"}</td>
                    <td>{row.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        <Card title="Details">
          <p>{matchedSummary}</p>

          {selectedPallet ? (
            <>
              <div style={{ marginBottom: "8px" }}>
                <Button variant="danger" onClick={() => void handleDeletePallet()}>
                  Delete pallet
                </Button>
              </div>
              <h3 className="subhead">Panels on Pallet</h3>
              {selectedPallet.items.length === 0 ? (
                <p>No panels on this pallet.</p>
              ) : (
                <table className="items-table">
                  <thead>
                    <tr>
                      <th>Slot</th>
                      <th>Serial</th>
                      <th>Added</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedPallet.items.map((item) => (
                      <tr key={item.id}>
                        <td>{item.slot_index}</td>
                        <td className="mono">{item.serial}</td>
                        <td>{new Date(item.added_at).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}

              <h3 className="subhead">Exports</h3>
              {exports.length === 0 ? (
                <p>No exports found for this pallet.</p>
              ) : (
                <ul className="flat-list">
                  {exports.map((item) => (
                    <li key={item.id}>
                      <span>
                        {item.file_name}
                        {" | "}
                        {item.template_type}
                        {" | Packout: "}
                        {item.packout_date ? new Date(item.packout_date).toLocaleDateString() : "-"}
                      </span>
                      <Button variant="secondary" onClick={() => void handleOpenExport(item.id, "pdf")}>
                        Open PDF
                      </Button>
                      <Button variant="secondary" onClick={() => void handleOpenExport(item.id, "xlsx")}>
                        Open XLSX
                      </Button>
                      <Button variant="secondary" onClick={() => void handleEditExport(item)}>
                        Edit Spreadsheet
                      </Button>
                    </li>
                  ))}
                </ul>
              )}

              {isEditorOpen ? (
                <section className="history-editor-panel">
                  <div className="history-editor-header">
                    <strong>Spreadsheet Editor</strong>
                    <div className="history-editor-actions">
                      <Button variant="secondary" onClick={closeEditor} disabled={isSavingEdit}>
                        Exit
                      </Button>
                      <Button onClick={() => void handleSaveSpreadsheet()} disabled={isEditorLoading || isSavingEdit}>
                        {isSavingEdit ? "Saving..." : "Save"}
                      </Button>
                    </div>
                  </div>
                  {isEditorLoading ? (
                    <p>Loading spreadsheet...</p>
                  ) : editableSheets.length === 0 ? (
                    <p>No sheets available to edit.</p>
                  ) : (
                    <>
                      <div className="history-editor-tabs">
                        {editableSheets.map((sheet, index) => (
                          <button
                            type="button"
                            key={sheet.name}
                            className={index === activeSheetIndex ? "history-editor-tab history-editor-tab--active" : "history-editor-tab"}
                            onClick={() => setActiveSheetIndex(index)}
                          >
                            {sheet.name}
                          </button>
                        ))}
                      </div>
                      <div className="history-editor-grid">
                        <Spreadsheet
                          data={editableSheets[activeSheetIndex]?.data ?? []}
                          onChange={handleSheetDataChange}
                        />
                      </div>
                    </>
                  )}
                </section>
              ) : null}

            </>
          ) : (
            <p>Select a pallet to load panel details and export actions.</p>
          )}
        </Card>
      </section>
    </AppFrame>
  );
}
