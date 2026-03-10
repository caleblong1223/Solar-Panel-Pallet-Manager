import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { invoke } from "@tauri-apps/api/core";
import AppFrame from "../components/layout/AppFrame";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import TextInput from "../components/ui/TextInput";
import { testServerConnectionNamed } from "../features/health";
import { isRuntimeSettingsLocked, loadRuntimeSettings, saveRuntimeSettings } from "../lib/runtimeConfig";
import { SYNC_STATE_EVENT, getSyncState, type SyncState } from "../sync/syncState";

export default function SettingsPage() {
  const settingsLocked = isRuntimeSettingsLocked();
  const initial = useMemo(() => loadRuntimeSettings(), []);
  const [primaryApiBaseUrl, setPrimaryApiBaseUrl] = useState(initial.primaryApiBaseUrl);
  const [fallbackApiBaseUrl, setFallbackApiBaseUrl] = useState(initial.fallbackApiBaseUrl);
  const [isTesting, setIsTesting] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [statusKind, setStatusKind] = useState<"success" | "warning" | "error" | null>(null);
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);
  const [backendMessage, setBackendMessage] = useState<string>("Checking local backend...");
  const [syncState, setSyncState] = useState<SyncState>(() => getSyncState());

  useEffect(() => {
    const refresh = () => setSyncState(getSyncState());
    refresh();
    window.addEventListener(SYNC_STATE_EVENT, refresh);
    const id = window.setInterval(refresh, 2000);
    return () => {
      window.removeEventListener(SYNC_STATE_EVENT, refresh);
      window.clearInterval(id);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    const checkBackend = async () => {
      const localApi = (fallbackApiBaseUrl || "http://127.0.0.1:8010/api/v1").trim();
      const result = await testServerConnectionNamed("Local backend", localApi);
      if (cancelled) {
        return;
      }
      setBackendHealthy(result.ok);
      setBackendMessage(result.message);
    };

    void checkBackend();
    const id = window.setInterval(() => {
      void checkBackend();
    }, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [fallbackApiBaseUrl]);

  const handleSave = (event: FormEvent) => {
    event.preventDefault();
    const saved = saveRuntimeSettings({
      primaryApiBaseUrl,
      fallbackApiBaseUrl,
      apiBaseUrl: primaryApiBaseUrl,
    });
    setPrimaryApiBaseUrl(saved.primaryApiBaseUrl);
    setFallbackApiBaseUrl(saved.fallbackApiBaseUrl);
    setStatusKind("success");
    setStatusMessage("Settings saved.");
  };

  const handleTestConnection = async (target: "primary" | "fallback") => {
    setIsTesting(true);
    setStatusMessage(null);
    setStatusKind(null);
    const result = await testServerConnectionNamed(
      target === "primary" ? "Primary server" : "Fallback server",
      target === "primary" ? primaryApiBaseUrl : fallbackApiBaseUrl
    );
    setStatusKind(result.ok ? "success" : "error");
    setStatusMessage(result.message);
    setIsTesting(false);
  };

  const handleOpenTerminal = async () => {
    try {
      await invoke("open_backend_terminal");
      setStatusKind("success");
      setStatusMessage("Backend terminal opened.");
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setStatusKind("error");
      setStatusMessage(message || "Failed to open backend terminal.");
    }
  };

  return (
    <AppFrame title="Settings">
      <main className="settings-page">
        <section className="settings-wrap">
          <Card title="Server Settings">
            <p className={`settings-status settings-status--${backendHealthy ? "success" : "warning"}`}>
              {backendHealthy === null ? "Backend status: checking..." : backendMessage}
            </p>
            <form className="builder-form" onSubmit={handleSave}>
              <TextInput
                label="Primary API Base URL (Central Server)"
                value={primaryApiBaseUrl}
                onChange={(event) => setPrimaryApiBaseUrl(event.target.value)}
                placeholder="http://192.168.1.20:8001/api/v1"
                required
                disabled={settingsLocked}
              />
              <TextInput
                label="Fallback API Base URL (Local Device)"
                value={fallbackApiBaseUrl}
                onChange={(event) => setFallbackApiBaseUrl(event.target.value)}
                placeholder="http://localhost:8010/api/v1"
                disabled={settingsLocked}
              />
              {settingsLocked ? (
                <p className="settings-status settings-status--warning">
                  API URLs are locked to the local bundled backend.
                </p>
              ) : null}
              <div className="settings-actions">
                <Button type="submit" disabled={settingsLocked}>
                  Save Settings
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  disabled={isTesting}
                  onClick={() => void handleTestConnection("primary")}
                >
                  {isTesting ? "Testing..." : "Test Primary"}
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  disabled={isTesting}
                  onClick={() => void handleTestConnection("fallback")}
                >
                  {isTesting ? "Testing..." : "Test Fallback"}
                </Button>
              </div>
            </form>

            {statusMessage ? (
              <p className={`settings-status settings-status--${statusKind ?? "warning"}`}>{statusMessage}</p>
            ) : null}
          </Card>

          <Card title="Sync Status">
            <p>
              <strong>Mode:</strong> {syncState.syncing ? "Syncing" : "Idle"}
            </p>
            <p>
              <strong>Pending:</strong> {syncState.pending_count}
            </p>
            <p>
              <strong>Needs Review:</strong> {syncState.needs_review_count}
            </p>
            <p>
              <strong>Failed:</strong> {syncState.failed_count}
            </p>
            <p>
              <strong>Last Sync:</strong>{" "}
              {syncState.last_sync_at ? new Date(syncState.last_sync_at).toLocaleString() : "Never"}
            </p>
            <Link className="inline-link" to="/sync-issues">
              Open Sync Issues
            </Link>
          </Card>

          <Card title="Backend Debug">
            <p>Need to inspect backend logs or run backend commands manually?</p>
            <div className="settings-actions">
              <Button type="button" variant="secondary" onClick={() => void handleOpenTerminal()}>
                Open Backend Terminal
              </Button>
            </div>
          </Card>
        </section>
      </main>
    </AppFrame>
  );
}
