const PALLET_ID_MAP_KEY = "pm2_sync_pallet_id_map";

type PalletIdMap = Record<string, number>;

function readMap(): PalletIdMap {
  const raw = localStorage.getItem(PALLET_ID_MAP_KEY);
  if (!raw) {
    return {};
  }
  try {
    const parsed = JSON.parse(raw) as PalletIdMap;
    return parsed ?? {};
  } catch {
    return {};
  }
}

function writeMap(next: PalletIdMap): void {
  localStorage.setItem(PALLET_ID_MAP_KEY, JSON.stringify(next));
}

export function setPalletIdMapping(localPalletId: number, serverPalletId: number): void {
  const map = readMap();
  map[String(localPalletId)] = serverPalletId;
  writeMap(map);
}

export function resolvePalletId(palletId: number): number {
  if (palletId > 0) {
    return palletId;
  }
  const mapped = readMap()[String(palletId)];
  return mapped ?? palletId;
}

