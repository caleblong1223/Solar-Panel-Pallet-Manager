import { FormEvent, useMemo, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import AppFrame from "../components/layout/AppFrame";
import { useToast } from "../components/notifications/ToastProvider";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import TextInput from "../components/ui/TextInput";
import { getPalletHistory, type AuditEvent } from "../features/audit";
import { searchBarcodes, type BarcodeSearchResult } from "../features/barcodes";
import { getExportDownloadUrl, listExportsByPallet, type ExportRecord } from "../features/exports";

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

  const runSearch = async (event: FormEvent) => {
    event.preventDefault();
    if (!token || !query.trim()) {
      return;
    }

    setIsLoading(true);
    try {
      const response = await searchBarcodes(token, { q: query.trim(), exact, limit: 100, sort: "created_at", order: "desc" });
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

  return (
    <AppFrame title="History Explorer">
      <section className="builder-grid">
        <Card title="Search by serial">
          <form className="builder-form" onSubmit={runSearch}>
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
    </AppFrame>
  );
}
