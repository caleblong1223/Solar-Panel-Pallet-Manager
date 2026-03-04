import { FormEvent, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import AppFrame from "../components/layout/AppFrame";
import { useToast } from "../components/notifications/ToastProvider";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import TextInput from "../components/ui/TextInput";
import { getExportDownloadUrl, listExportsByPallet, type ExportRecord } from "../features/exports";
import { getImportBatch, uploadSimulatorFile, type SimImportBatch } from "../features/simulator";
import { createExport } from "../features/pallets";

const TEMPLATE_OPTIONS = ["200WT", "220WT", "220M6", "330WT", "450WT", "450BT"] as const;

export default function ImportExportPage() {
  const { token } = useAuth();
  const { notify } = useToast();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [latestBatch, setLatestBatch] = useState<SimImportBatch | null>(null);
  const [batchLookupId, setBatchLookupId] = useState("");

  const [createPalletId, setCreatePalletId] = useState("");
  const [createTemplate, setCreateTemplate] = useState<(typeof TEMPLATE_OPTIONS)[number]>("450WT");

  const [exportPalletFilter, setExportPalletFilter] = useState("");
  const [exportRows, setExportRows] = useState<ExportRecord[]>([]);

  const [isBusy, setIsBusy] = useState(false);

  const handleUpload = async (event: FormEvent) => {
    event.preventDefault();
    if (!token || !selectedFile) {
      notify("Choose a simulator file first", "warning");
      return;
    }

    setIsBusy(true);
    try {
      const batch = await uploadSimulatorFile(token, selectedFile);
      setLatestBatch(batch);
      setBatchLookupId(String(batch.id));
      notify(`Import batch #${batch.id} created`, "success");
    } catch {
      notify("Import upload failed", "error");
    } finally {
      setIsBusy(false);
    }
  };

  const handleFetchBatch = async () => {
    if (!token) {
      return;
    }
    const id = Number.parseInt(batchLookupId, 10);
    if (!Number.isFinite(id)) {
      notify("Enter a valid batch ID", "warning");
      return;
    }

    setIsBusy(true);
    try {
      const batch = await getImportBatch(token, id);
      setLatestBatch(batch);
      notify(`Loaded batch #${batch.id}`, "success");
    } catch {
      notify("Batch not found", "error");
    } finally {
      setIsBusy(false);
    }
  };

  const handleCreateExport = async (event: FormEvent) => {
    event.preventDefault();
    if (!token) {
      return;
    }

    const palletId = Number.parseInt(createPalletId, 10);
    if (!Number.isFinite(palletId)) {
      notify("Enter a valid pallet ID", "warning");
      return;
    }

    setIsBusy(true);
    try {
      const created = await createExport(token, { pallet_id: palletId, template_type: createTemplate });
      notify(`Created export #${created.id}`, "success");
      if (exportPalletFilter === String(palletId)) {
        const listed = await listExportsByPallet(token, palletId);
        setExportRows(listed.exports);
      }
    } catch {
      notify("Failed to create export", "error");
    } finally {
      setIsBusy(false);
    }
  };

  const handleListExports = async (event: FormEvent) => {
    event.preventDefault();
    if (!token) {
      return;
    }

    const palletId = Number.parseInt(exportPalletFilter, 10);
    if (!Number.isFinite(palletId)) {
      notify("Enter a valid pallet ID filter", "warning");
      return;
    }

    setIsBusy(true);
    try {
      const response = await listExportsByPallet(token, palletId);
      setExportRows(response.exports);
      notify(`Loaded ${response.total} exports`, "success");
    } catch {
      notify("Failed to list exports", "error");
    } finally {
      setIsBusy(false);
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
      notify("Failed to open export", "error");
    }
  };

  return (
    <AppFrame title="Import Center + Export Library">
      <section className="builder-grid">
        <Card title="Simulator import">
          <form className="builder-form" onSubmit={handleUpload}>
            <label className="ui-input-label">
              <span>Choose source file (.csv/.xlsx/.xls)</span>
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

          <div className="builder-form" style={{ marginTop: "12px" }}>
            <TextInput
              label="Fetch batch by ID"
              inputMode="numeric"
              value={batchLookupId}
              onChange={(event) => setBatchLookupId(event.target.value)}
            />
            <Button variant="secondary" disabled={isBusy} onClick={() => void handleFetchBatch()}>
              Load Batch
            </Button>
          </div>

          {latestBatch ? (
            <div className="builder-meta" style={{ marginTop: "12px" }}>
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

        <Card title="Create export">
          <form className="builder-form" onSubmit={handleCreateExport}>
            <TextInput
              label="Pallet ID"
              inputMode="numeric"
              value={createPalletId}
              onChange={(event) => setCreatePalletId(event.target.value)}
              required
            />
            <label className="ui-input-label">
              <span>Template</span>
              <select
                className="ui-select"
                value={createTemplate}
                onChange={(event) => setCreateTemplate(event.target.value as (typeof TEMPLATE_OPTIONS)[number])}
              >
                {TEMPLATE_OPTIONS.map((template) => (
                  <option key={template} value={template}>
                    {template}
                  </option>
                ))}
              </select>
            </label>
            <Button type="submit" disabled={isBusy}>
              Create Export
            </Button>
          </form>
        </Card>
      </section>

      <section className="card-grid">
        <Card title="Export library">
          <form className="builder-form" onSubmit={handleListExports}>
            <TextInput
              label="Filter by pallet ID"
              inputMode="numeric"
              value={exportPalletFilter}
              onChange={(event) => setExportPalletFilter(event.target.value)}
              required
            />
            <Button type="submit" disabled={isBusy}>
              Load Exports
            </Button>
          </form>

          {exportRows.length === 0 ? (
            <p style={{ marginTop: "12px" }}>No export rows loaded.</p>
          ) : (
            <ul className="flat-list" style={{ marginTop: "12px" }}>
              {exportRows.map((row) => (
                <li key={row.id}>
                  <span>
                    #{row.id} {row.file_name}
                  </span>
                  <Button variant="secondary" onClick={() => void handleOpenExport(row.id)}>
                    Open
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </section>
    </AppFrame>
  );
}
