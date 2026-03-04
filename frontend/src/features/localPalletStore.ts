import type { Pallet } from "./pallets";

const LOCAL_PALLETS_KEY = "pm2_local_pallets";

function readPallets(): Pallet[] {
  const raw = localStorage.getItem(LOCAL_PALLETS_KEY);
  if (!raw) {
    return [];
  }
  try {
    const parsed = JSON.parse(raw) as Pallet[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writePallets(pallets: Pallet[]): void {
  localStorage.setItem(LOCAL_PALLETS_KEY, JSON.stringify(pallets));
}

export function getAllLocalPallets(): Pallet[] {
  return readPallets();
}

export function replaceAllLocalPallets(pallets: Pallet[]): void {
  writePallets(pallets);
}

export function listLocalPalletsByStatus(status = "active"): Pallet[] {
  return readPallets().filter((pallet) => pallet.status === status && pallet.deleted_at === null);
}

export function findLocalPalletById(palletId: number): Pallet | null {
  return readPallets().find((pallet) => pallet.id === palletId) ?? null;
}

export function upsertLocalPallet(nextPallet: Pallet): Pallet {
  const pallets = readPallets();
  const index = pallets.findIndex((pallet) => pallet.id === nextPallet.id);
  if (index === -1) {
    pallets.push(nextPallet);
  } else {
    pallets[index] = nextPallet;
  }
  writePallets(pallets);
  return nextPallet;
}

