import { invoke } from "@tauri-apps/api/core";

export async function openWithSystem(target: string): Promise<void> {
  try {
    await invoke("open_with_system", { target });
    return;
  } catch {
    // Browser fallback works for web contexts and non-tauri dev sessions.
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
  try {
    await invoke("download_and_open_with_system", {
      url,
      bearer_token: options?.bearerToken ?? null,
      file_name: options?.fileName ?? null,
    });
    return;
  } catch {
    // Browser fallback for non-tauri sessions.
  }

  window.open(url, "_blank", "noopener,noreferrer");
}

