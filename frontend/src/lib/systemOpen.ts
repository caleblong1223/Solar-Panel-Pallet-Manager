export async function openWithSystem(target: string): Promise<void> {
  // Browser fallback works for both web and desktop contexts.
  window.open(target, "_blank", "noopener,noreferrer");
}

