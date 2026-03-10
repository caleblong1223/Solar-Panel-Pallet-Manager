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

