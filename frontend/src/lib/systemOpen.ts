import { invoke } from "@tauri-apps/api/core";

function isTauriRuntime(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

function normalizeInvokeError(error: unknown, fallbackMessage: string): Error {
  if (error instanceof Error) {
    return error;
  }
  if (typeof error === "string" && error.trim()) {
    return new Error(error);
  }
  if (error && typeof error === "object") {
    const message = "message" in error && typeof error.message === "string" ? error.message : JSON.stringify(error);
    if (message && message !== "{}") {
      return new Error(message);
    }
  }
  return new Error(fallbackMessage);
}

export async function openWithSystem(target: string): Promise<void> {
  if (isTauriRuntime()) {
    try {
      await invoke("open_with_system", { target });
      return;
    } catch (error) {
      throw normalizeInvokeError(error, "Failed to open file with system app");
    }
  }

  window.open(target, "_blank", "noopener,noreferrer");
}

export async function downloadAndOpenWithSystem(
  url: string,
  options?: {
    bearerToken?: string;
    fileName?: string;
  }
): Promise<void> {
  if (isTauriRuntime()) {
    try {
      await invoke("download_and_open_with_system", {
        url,
        bearer_token: options?.bearerToken ?? null,
        file_name: options?.fileName ?? null,
      });
      return;
    } catch (error) {
      throw normalizeInvokeError(error, "Failed to download and open file");
    }
  }

  window.open(url, "_blank", "noopener,noreferrer");
}

export async function renderLocalWorkbookPdfAndOpen(workbookPath: string): Promise<void> {
  if (isTauriRuntime()) {
    try {
      await invoke("render_local_workbook_pdf_and_open", { workbook_path: workbookPath });
      return;
    } catch (error) {
      throw normalizeInvokeError(error, "Failed to render workbook PDF");
    }
  }

  window.open(workbookPath, "_blank", "noopener,noreferrer");
}

