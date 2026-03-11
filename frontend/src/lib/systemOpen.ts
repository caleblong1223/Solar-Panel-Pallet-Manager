import { invoke } from "@tauri-apps/api/core";

function isTauriRuntime(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

export async function openWithSystem(target: string): Promise<void> {
  if (isTauriRuntime()) {
    await invoke("open_with_system", { target });
    return;
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
    await invoke("download_and_open_with_system", {
      url,
      bearer_token: options?.bearerToken ?? null,
      file_name: options?.fileName ?? null,
    });
    return;
  }

  window.open(url, "_blank", "noopener,noreferrer");
}

