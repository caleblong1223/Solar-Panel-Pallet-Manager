import { FormEvent, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import AppFrame from "../components/layout/AppFrame";
import { useToast } from "../components/notifications/ToastProvider";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import TextInput from "../components/ui/TextInput";
import { searchBarcodes, type BarcodeSearchResult } from "../features/barcodes";
import { uploadSimulatorFile, type SimImportBatch } from "../features/simulator";

export default function ImportExportPage() {
  const { token } = useAuth();
  const { notify } = useToast();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [latestBatch, setLatestBatch] = useState<SimImportBatch | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  const [searchSerial, setSearchSerial] = useState("");
  const [searchResults, setSearchResults] = useState<BarcodeSearchResult[]>([]);
  const [searchBusy, setSearchBusy] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  const handleUpload = async (event: FormEvent) => {
    event.preventDefault();
    if (!token || !selectedFile) {
      notify("Choose a simulator file first", "warning");
      return;
    }

    setIsBusy(true);
    setLatestBatch(null);
    try {
      const batch = await uploadSimulatorFile(token, selectedFile);
      setLatestBatch(batch);
      notify(`Import batch #${batch.id} created`, "success");
    } catch {
      notify("Import upload failed", "error");
    } finally {
      setIsBusy(false);
    }
  };

  const handleSearch = async (event: FormEvent) => {
    event.preventDefault();
    const serial = searchSerial.trim();
    if (!token || !serial) {
      notify("Enter a serial to search", "warning");
      return;
    }

    setSearchBusy(true);
    setSearchResults([]);
    setHasSearched(false);
    try {
      const response = await searchBarcodes(token, { q: serial, exact: false, limit: 50 });
      const simOnly = response.results.filter((r) => r.source === "sim_panel");
      setSearchResults(simOnly);
      setHasSearched(true);
      if (simOnly.length === 0) {
        notify("No Sun Simulator data found for this serial", "warning");
      }
    } catch {
      notify("Search failed", "error");
    } finally {
      setSearchBusy(false);
    }
  };

  return (
    <AppFrame title="Sun Simulator Import">
      <section className="builder-grid">
        <Card title="Import Sun Simulator data">
          <p style={{ marginBottom: "12px", color: "var(--color-text-secondary)" }}>
            Upload a file (.csv, .xlsx, .xls) from the Sun Simulator to import panel test data into the database.
          </p>
          <form className="builder-form" onSubmit={handleUpload}>
            <label className="ui-input-label">
              <span>Choose source file</span>
              <input
                className="ui-input"
                type="file"
                accept=".csv,.xlsx,.xls"
                onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
              />
            </label>
            <Button type="submit" disabled={isBusy || !selectedFile}>
              Upload and Import
            </Button>
          </form>

          {latestBatch ? (
            <div className="builder-meta" style={{ marginTop: "16px" }}>
              <p>
                <strong>Batch:</strong> #{latestBatch.id}
              </p>
              <p>
                <strong>Status:</strong> {latestBatch.status}
              </p>
              <p>
                <strong>Rows:</strong> {latestBatch.rows_imported ?? 0} imported / {latestBatch.rows_rejected ?? 0} rejected / {latestBatch.rows_total ?? 0} total
              </p>
            </div>
          ) : null}
        </Card>

        <Card title="Search: is this panel in the database?">
          <p style={{ marginBottom: "12px", color: "var(--color-text-secondary)" }}>
            Enter a panel serial to check whether its Sun Simulator information has been imported.
          </p>
          <form className="builder-form" onSubmit={handleSearch}>
            <TextInput
              label="Panel serial"
              value={searchSerial}
              onChange={(event) => setSearchSerial(event.target.value)}
              placeholder="e.g. serial number or barcode"
            />
            <Button type="submit" disabled={searchBusy}>
              Search
            </Button>
          </form>

          {searchResults.length > 0 ? (
            <div style={{ marginTop: "16px" }}>
              <p className="builder-meta">
                <strong>Found {searchResults.length} Sun Simulator record(s):</strong>
              </p>
              <ul className="flat-list" style={{ marginTop: "8px" }}>
                {searchResults.map((r) => (
                  <li key={`${r.sim_panel_id ?? 0}-${r.serial}-${r.sim_test_timestamp ?? ""}`}>
                    <span>
                      {r.serial}
                      {r.sim_panel_type != null ? ` · ${r.sim_panel_type}` : ""}
                      {r.sim_result != null ? ` · ${r.sim_result}` : ""}
                      {r.sim_test_timestamp != null ? ` · ${r.sim_test_timestamp}` : ""}
                      {r.sim_batch_id != null ? ` (batch #${r.sim_batch_id})` : ""}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ) : searchBusy ? null : hasSearched && searchResults.length === 0 ? (
            <p style={{ marginTop: "12px", color: "var(--color-text-secondary)" }}>
              No Sun Simulator data found for this serial.
            </p>
          ) : null}
        </Card>
      </section>
    </AppFrame>
  );
}
