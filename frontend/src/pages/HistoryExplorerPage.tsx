import { FormEvent, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
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
  applyExportWorkbookEdits,
  downloadExportWorkbook,
  getMergedExportsPdfEndpoint,
  getExportDownloadUrl,
  listExportsByPallet,
  type ExportRecord,
} from "../features/exports";
import { listCustomers, type Customer } from "../features/customers";
import { openWithSystem } from "../lib/systemOpen";

type SheetCell = CellBase<string>;
type EditableSheet = {
  name: string;
  data: Matrix<SheetCell>;
};

type SpreadsheetEditorProps = {
  sheetKey: string;
  sheetData: Matrix<SheetCell>;
  onDataChange: (nextData: Matrix<SheetCell>) => void;
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

function SpreadsheetEditor({ sheetKey, sheetData, onDataChange }: SpreadsheetEditorProps) {
  const [draftData, setDraftData] = useState(sheetData);
  const topScrollRef = useRef<HTMLDivElement | null>(null);
  const gridScrollRef = useRef<HTMLDivElement | null>(null);
  const topScrollInnerRef = useRef<HTMLDivElement | null>(null);
  const syncingScrollRef = useRef<"top" | "grid" | null>(null);

  useEffect(() => {
    setDraftData(sheetData);
  }, [sheetKey, sheetData]);

  const syncScrollMetrics = useCallback(() => {
    const topScroll = topScrollRef.current;
    const gridScroll = gridScrollRef.current;
    const topScrollInner = topScrollInnerRef.current;
    if (!topScroll || !gridScroll || !topScrollInner) {
      return;
    }
    topScrollInner.style.width = `${gridScroll.scrollWidth}px`;
    topScroll.scrollLeft = gridScroll.scrollLeft;
  }, []);

  useLayoutEffect(() => {
    syncScrollMetrics();
  }, [draftData, syncScrollMetrics]);

  useEffect(() => {
    const topScroll = topScrollRef.current;
    const gridScroll = gridScrollRef.current;
    if (!topScroll || !gridScroll) {
      return;
    }

    const handleTopScroll = () => {
      if (syncingScrollRef.current === "grid") {
        syncingScrollRef.current = null;
        return;
      }
      syncingScrollRef.current = "top";
      gridScroll.scrollLeft = topScroll.scrollLeft;
    };

    const handleGridScroll = () => {
      if (syncingScrollRef.current === "top") {
        syncingScrollRef.current = null;
        return;
      }
      syncingScrollRef.current = "grid";
      topScroll.scrollLeft = gridScroll.scrollLeft;
    };

    const resizeObserver = typeof ResizeObserver !== "undefined" ? new ResizeObserver(() => syncScrollMetrics()) : null;
    resizeObserver?.observe(gridScroll);
    const gridTable = gridScroll.querySelector("table");
    if (gridTable instanceof HTMLElement) {
      resizeObserver?.observe(gridTable);
    }
    window.addEventListener("resize", syncScrollMetrics);
    topScroll.addEventListener("scroll", handleTopScroll, { passive: true });
    gridScroll.addEventListener("scroll", handleGridScroll, { passive: true });

    syncScrollMetrics();

    return () => {
      resizeObserver?.disconnect();
      window.removeEventListener("resize", syncScrollMetrics);
      topScroll.removeEventListener("scroll", handleTopScroll);
      gridScroll.removeEventListener("scroll", handleGridScroll);
    };
  }, [syncScrollMetrics]);

  const handleChange = useCallback(
    (nextData: Matrix<SheetCell>) => {
      setDraftData(nextData);
      onDataChange(nextData);
    },
    [onDataChange]
  );

  return (
    <div className="history-editor-shell">
      <div ref={topScrollRef} className="history-editor-scrollbar" aria-label="Spreadsheet horizontal scroll">
        <div ref={topScrollInnerRef} className="history-editor-scrollbar__inner" />
      </div>
      <div ref={gridScrollRef} className="history-editor-grid">
        <Spreadsheet data={draftData} onChange={handleChange} />
      </div>
    </div>
  );
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
  const [selectedPalletIds, setSelectedPalletIds] = useState<number[]>([]);
  const [isMerging, setIsMerging] = useState(false);
  const editableSheetsRef = useRef<EditableSheet[]>([]);

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
        response = await listPallets(apiToken, "active", { timeoutMs: 10000 });
      }
      setPallets(response.pallets);
      setSelectedPalletIds((previous) => previous.filter((id) => response.pallets.some((pallet) => pallet.id === id)));
      setSelectedPalletId((previous) => (previous && response.pallets.some((pallet) => pallet.id === previous) ? previous : null));
      if (response.total === 0) {
        notify("No history records found", "warning");
      }
      return response.pallets;
    } catch {
      await new Promise((resolve) => window.setTimeout(resolve, 800));
      try {
        const retry = await listPallets(apiToken, "completed", { timeoutMs: 10000 });
        setPallets(retry.pallets);
        setSelectedPalletIds((previous) => previous.filter((id) => retry.pallets.some((pallet) => pallet.id === id)));
        setSelectedPalletId((previous) => (previous && retry.pallets.some((pallet) => pallet.id === previous) ? previous : null));
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
          const day = start.getDay() || 7;
          start.setDate(start.getDate() - (day - 1));
          start.setHours(0, 0, 0, 0);
          from = start;
          break;
        }
        case "month": {
          from = new Date(now.getFullYear(), now.getMonth(), 1);
          break;
        }
        case "year": {
          from = new Date(now.getFullYear(), 0, 1);
          break;
        }
      }
      if (from) {
        filtered = filtered.filter((pallet) => {
          const raw = pallet.completed_at ? new Date(pallet.completed_at) : new Date(pallet.created_at);
          if (Number.isNaN(raw.getTime())) return false;
          return raw >= from;
        });
      }
    }

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
        filtered.sort((a, b) => new Date(a.completed_at ?? a.created_at).getTime() - new Date(b.completed_at ?? b.created_at).getTime());
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
        filtered.sort((a, b) => new Date(b.completed_at ?? b.created_at).getTime() - new Date(a.completed_at ?? a.created_at).getTime());
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
      setPallets((previous) => previous.map((entry) => (entry.id === palletId ? palletRow : entry)));
      setExports(exportRows.exports);
    } catch {
      notify("Failed to load pallet details", "error");
    }
  };

  const handleOpenExport = async (exportId: number, format: "pdf" | "xlsx") => {
    try {
      const response = await getExportDownloadUrl(apiToken, exportId, format);
      await openWithSystem(response.download_url);
    } catch (error) {
      const message = error instanceof Error ? error.message : `Failed to open ${format.toUpperCase()}`;
      notify(message, "error");
    }
  };

  const handleDeletePallet = async () => {
    if (!selectedPalletId) {
      return;
    }
    try {
      await deletePallet(apiToken, selectedPalletId);
      setPallets((prev) => prev.filter((row) => row.id !== selectedPalletId));
      setSelectedPalletIds((prev) => prev.filter((id) => id !== selectedPalletId));
      setSelectedPalletId(null);
      setExports([]);
      closeEditor();
      notify("Pallet deleted", "success");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to delete pallet";
      notify(message, "error");
    }
  };

  const closeEditor = () => {
    setIsEditorOpen(false);
    setIsEditorLoading(false);
    setIsSavingEdit(false);
    setEditingExport(null);
    setEditableSheets([]);
    editableSheetsRef.current = [];
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
        // Keep editor aligned with required export layout by hiding FF column text.
        if (rows.length >= 4 && Array.isArray(rows[3])) {
          const ffIndex = rows[3].findIndex((value) => String(value ?? "").trim().toUpperCase().startsWith("FF"));
          if (ffIndex >= 0) {
            rows[3][ffIndex] = "";
            for (let rowIndex = 4; rowIndex < rows.length; rowIndex += 1) {
              if (!Array.isArray(rows[rowIndex])) continue;
              rows[rowIndex][ffIndex] = "";
            }
          }
        }
        return {
          name,
          data: matrixFromRows(rows),
        };
      });
      editableSheetsRef.current = nextSheets;
      setEditableSheets(nextSheets);
    } catch (error) {
      closeEditor();
      const message = error instanceof Error ? error.message : "Failed to load export workbook for editing";
      notify(message, "error");
    } finally {
      setIsEditorLoading(false);
    }
  };

  const handleSheetDataChange = useCallback(
    (nextData: Matrix<SheetCell>) => {
      const currentSheets = editableSheetsRef.current;
      if (!currentSheets[activeSheetIndex]) {
        return;
      }
      currentSheets[activeSheetIndex] = {
        ...currentSheets[activeSheetIndex],
        data: nextData,
      };
    },
    [activeSheetIndex]
  );

  const handleSaveSpreadsheet = async () => {
    if (!editingExport || editableSheets.length === 0) {
      return;
    }
    setIsSavingEdit(true);
    try {
      const sheets = editableSheetsRef.current.map((sheet) => ({
        name: sheet.name,
        data: sheet.data.map((row) => row.map((cell) => (cell?.value ?? ""))),
      }));
      await applyExportWorkbookEdits(apiToken, editingExport.id, sheets);
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

  const togglePalletSelection = (palletId: number, checked: boolean) => {
    setSelectedPalletIds((previous) => {
      if (checked) {
        if (previous.includes(palletId)) return previous;
        return [...previous, palletId];
      }
      return previous.filter((id) => id !== palletId);
    });
  };

  useEffect(() => {
    if (selectedPalletIds.length > 1) {
      closeEditor();
    }
  }, [selectedPalletIds.length]);

  const handleMergeSelectedPallets = async () => {
    if (selectedPalletIds.length < 2) {
      notify("Select at least 2 pallets", "warning");
      return;
    }
    setIsMerging(true);
    try {
      const exportsByPallet = await Promise.all(selectedPalletIds.map((palletId) => listExportsByPallet(apiToken, palletId)));
      const exportIds = exportsByPallet
        .map((result) => result.exports[0]?.id)
        .filter((value): value is number => typeof value === "number");
      if (exportIds.length < 2) {
        notify("Need at least 2 pallets with exports to merge", "warning");
        return;
      }
      const endpoint = getMergedExportsPdfEndpoint(exportIds);
      await openWithSystem(endpoint);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to merge selected pallets";
      notify(message, "error");
    } finally {
      setIsMerging(false);
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
                  <th>Select</th>
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
                    <td>
                      <input
                        type="checkbox"
                        checked={selectedPalletIds.includes(row.id)}
                        onClick={(event) => event.stopPropagation()}
                        onChange={(event) => togglePalletSelection(row.id, event.target.checked)}
                      />
                    </td>
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

          {selectedPalletIds.length > 1 ? (
            <>
              <p>{selectedPalletIds.length} pallets selected.</p>
              <Button onClick={() => void handleMergeSelectedPallets()} disabled={isMerging}>
                {isMerging ? "Merging..." : "Merge Selected XLSX To Printable PDF"}
              </Button>
            </>
          ) : selectedPallet ? (
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
            </>
          ) : (
            <p>Select a pallet to load panel details and export actions.</p>
          )}
        </Card>
      </section>

      {isEditorOpen ? (
        <section className="builder-grid" style={{ marginTop: "12px" }}>
          <Card title="Spreadsheet Editor">
            <section className="history-editor-panel">
              <div className="history-editor-header">
                <strong>{editingExport?.file_name ?? "Spreadsheet"}</strong>
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
                  <SpreadsheetEditor
                    sheetKey={`${activeSheetIndex}-${editableSheets[activeSheetIndex]?.name ?? "sheet"}`}
                    sheetData={editableSheets[activeSheetIndex]?.data ?? []}
                    onDataChange={handleSheetDataChange}
                  />
                </>
              )}
            </section>
          </Card>
        </section>
      ) : null}
    </AppFrame>
  );
}
