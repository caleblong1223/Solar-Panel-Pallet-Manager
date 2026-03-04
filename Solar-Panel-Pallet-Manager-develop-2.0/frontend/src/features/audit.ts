import { apiRequest } from "../lib/api";

export type AuditEvent = {
  id: number;
  actor_user_id: number | null;
  event_type: string;
  resource_type: string;
  resource_id: string | null;
  outcome: string;
  message: string | null;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
};

export async function getPalletHistory(token: string, palletId: number) {
  return apiRequest<AuditEvent[]>(`/pallets/${palletId}/history`, "GET", token);
}
