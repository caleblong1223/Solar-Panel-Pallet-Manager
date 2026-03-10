import { FormEvent, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import AppFrame from "../components/layout/AppFrame";
import { useToast } from "../components/notifications/ToastProvider";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import TextInput from "../components/ui/TextInput";
import { getExportDownloadUrl, listExports, type ExportRecord } from "../features/exports";
import { openWithSystem } from "../lib/systemOpen";

const TEMPLATE_OPTIONS = ["", "200WT", "220WT", "220M6", "330WT", "450WT", "450BT"];

export default function ExportsPage() {
  const { token } = useAuth();
  const { notify } = useToast();

  const [palletNumber, setPalletNumber] = useState("");
  const [templateType, setTemplateType] = useState("");
  const [createdFrom, setCreatedFrom] = useState("");
  const [createdTo, setCreatedTo] = useState("");

  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<ExportRecord[]>([]);

  const handleSearch = async (event: FormEvent) => {
    event.preventDefault();
    let palletId: number | undefined;
    if (palletNumber.trim()) {
      const parsed = Number(palletNumber.trim());
      if (!Number.isFinite(parsed) || parsed <= 0) {
        notify("Pallet number must be a positive number", "warning");
        return;
      }
      palletId = parsed;
    }

    const toIso = (date: string, endOfDay: boolean) => {
      if (!date) return undefined;
      const base = endOfDay ? "T23:59:59" : "T00:00:00";
      return `${date}${base}`;
    };

    setIsLoading(true);
    try {
      const response = await listExports(token ?? "", {
        palletId,
        templateType: templateType || undefined,
        createdFrom: toIso(createdFrom, false),
        createdTo: toIso(createdTo, true),
        limit: 100,
        offset: 0,
      });
      setResults(response.exports);
      if (response.total === 0) {
        notify("No exports found for the given filters", "warning");
      } else {
        notify(`Found ${response.total} export(s)`, "success");
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to load exports";
      notify(message, "error");
    } finally {
      setIsLoading(false);
    }
  };

  const handleOpen = async (exportId: number) => {
    try {
      const response = await getExportDownloadUrl(token ?? "", exportId, "pdf");
      await openWithSystem(response.download_url);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to open export";
      notify(message, "error");
    }
  };

  return (
    <AppFrame title="Export Library">
      <section className="builder-grid">
        <Card title="Filters">
          <form className="builder-form" onSubmit={handleSearch}>
            <TextInput
              label="Pallet number"
              value={palletNumber}
              onChange={(event) => setPalletNumber(event.target.value)}
              placeholder="e.g. 123"
            />
            <label className="ui-input-label">
              <span>Template type</span>
              <select
                className="ui-select"
                value={templateType}
                onChange={(event) => setTemplateType(event.target.value)}
              >
                {TEMPLATE_OPTIONS.map((option) => (
                  <option key={option || "any"} value={option}>
                    {option || "Any template"}
                  </option>
                ))}
              </select>
            </label>
            <div style={{ display: "flex", gap: "8px" }}>
              <label className="ui-input-label" style={{ flex: 1 }}>
                <span>From date</span>
                <input
                  className="ui-input"
                  type="date"
                  value={createdFrom}
                  onChange={(event) => setCreatedFrom(event.target.value)}
                />
              </label>
              <label className="ui-input-label" style={{ flex: 1 }}>
                <span>To date</span>
                <input
                  className="ui-input"
                  type="date"
                  value={createdTo}
                  onChange={(event) => setCreatedTo(event.target.value)}
                />
              </label>
            </div>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? "Searching..." : "Search"}
            </Button>
          </form>
        </Card>

        <Card title="Exports">
          {results.length === 0 ? (
            <p style={{ marginTop: "12px", color: "var(--color-text-secondary)" }}>
              No exports loaded. Use the filters to search.
            </p>
          ) : (
            <table className="items-table" style={{ marginTop: "12px" }}>
              <thead>
                <tr>
                  <th>Created</th>
                  <th>Pallet ID</th>
                  <th>Template</th>
                  <th>File name</th>
                  <th>Size</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {results.map((row) => (
                  <tr key={row.id}>
                    <td>{new Date(row.created_at).toLocaleString()}</td>
                    <td>{row.pallet_id}</td>
                    <td>{row.template_type}</td>
                    <td>{row.file_name}</td>
                    <td>{row.size_bytes != null ? `${(row.size_bytes / 1024).toFixed(1)} KB` : "-"}</td>
                    <td style={{ textAlign: "right" }}>
                      <Button variant="secondary" onClick={() => void handleOpen(row.id)}>
                        Open
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </section>
    </AppFrame>
  );
}

