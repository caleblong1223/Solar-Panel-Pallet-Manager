import { ChangeEvent, FormEvent, useRef, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import AppFrame from "../components/layout/AppFrame";
import { useToast } from "../components/notifications/ToastProvider";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import TextInput from "../components/ui/TextInput";
import { searchBarcodes, type BarcodeSearchResult } from "../features/barcodes";
import { uploadSimulatorFile, type SimImportBatch } from "../features/simulator";

type UploadResult = {
  fileName: string;
  batch?: SimImportBatch;
  error?: string;
};

export default function ImportExportPage() {
  const { token } = useAuth();
  const { notify } = useToast();

  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadResults, setUploadResults] = useState<UploadResult[]>([]);
  const [isBusy, setIsBusy] = useState(false);

  const [searchSerial, setSearchSerial] = useState("");
  const [searchResults, setSearchResults] = useState<BarcodeSearchResult[]>([]);
  const [searchBusy, setSearchBusy] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const formatSimTimestamp = (value: string | null | undefined) => {
    if (!value) return null;
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return value;
    return parsed.toLocaleString();
  };

  const formatElectrical = (label: string, value: number | null | undefined, digits = 2) => {
    if (value == null) return null;
    return `${label}: ${value.toFixed(digits)}`;
  };

  const handleUpload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (selectedFiles.length === 0) {
      notify("Choose at least one simulator file first", "warning");
      return;
    }

    setIsBusy(true);
    setUploadResults([]);
    try {
      const summary: UploadResult[] = [];
      for (const file of selectedFiles) {
        try {
          const batch = await uploadSimulatorFile(file);
          summary.push({ fileName: file.name, batch });
        } catch (error) {
          const message = error instanceof Error ? error.message : "Import upload failed";
          summary.push({ fileName: file.name, error: message });
        }
      }
      setUploadResults(summary);
      const successCount = summary.filter((item) => item.batch).length;
      const failureCount = summary.filter((item) => item.error).length;
      if (successCount > 0) {
        notify(`Imported ${successCount} ${successCount === 1 ? "file" : "files"}`, "success");
      }
      if (failureCount > 0) {
        notify(`${failureCount} ${failureCount === 1 ? "file" : "files"} failed to import`, "error");
      }
    } finally {
      setIsBusy(false);
      setSelectedFiles([]);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleSearch = async (event: FormEvent) => {
    event.preventDefault();
    const serial = searchSerial.trim();
    if (!serial) {
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
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Unknown error";
      notify(`Search failed: ${detail}`, "error");
    } finally {
      setSearchBusy(false);
    }
  };

  return (
    <AppFrame title="Sun Simulator Import">
      <section className="builder-grid">
        <Card title="Import Sun Simulator data">
          <p style={{ marginBottom: "12px", color: "var(--color-text-secondary)" }}>
            Upload one or more files (.csv, .xlsx, .xls) from the Sun Simulator to import panel test data into the database.
          </p>
          <form className="builder-form" onSubmit={handleUpload}>
            <label className="ui-input-label">
              <span>Choose source file(s)</span>
              <input
                className="ui-input"
                type="file"
                accept=".csv,.xlsx,.xls"
                multiple
                ref={fileInputRef}
                onChange={(event: ChangeEvent<HTMLInputElement>) =>
                  setSelectedFiles(event.target.files ? Array.from(event.target.files) : [])
                }
              />
            </label>
            <Button type="submit" disabled={isBusy || selectedFiles.length === 0}>
              Upload and Import
            </Button>
          </form>
          {selectedFiles.length > 0 && (
            <p className="builder-meta" style={{ marginTop: "12px" }}>
              Selected {selectedFiles.length} file{selectedFiles.length === 1 ? "" : "s"}:{" "}
              {selectedFiles.map((file) => file.name).join(", ")}
            </p>
          )}

          {uploadResults.length > 0 && (
            <div className="builder-meta" style={{ marginTop: "16px" }}>
              <p>
                <strong>Import results</strong>
              </p>
              <ul className="flat-list" style={{ marginTop: "8px" }}>
                {uploadResults.map((result) => (
                  <li key={result.fileName}>
                    <strong>{result.fileName}</strong>
                    {result.batch ? (
                      <span>
                        {` · batch #${result.batch.id} · ${result.batch.status} · `}
                        {`${result.batch.rows_imported ?? 0} imported / ${result.batch.rows_rejected ?? 0} rejected / ${result.batch.rows_total ?? 0} total`}
                      </span>
                    ) : result.error ? (
                      <span>{` · failed: ${result.error}`}</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          )}
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
                      {r.sim_test_timestamp != null ? ` · ${formatSimTimestamp(r.sim_test_timestamp)}` : ""}
                    </span>
                    <div style={{ marginTop: "4px", color: "var(--color-text-secondary)", fontSize: "0.9rem" }}>
                      {[
                        formatElectrical("Pm", r.sim_watts),
                        formatElectrical("Isc", r.sim_isc),
                        formatElectrical("Voc(V)", r.sim_voc),
                        formatElectrical("Ipm", r.sim_imp),
                        formatElectrical("Vpm(V)", r.sim_vmp),
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </div>
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
