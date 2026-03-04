import { apiRequest } from "../lib/api";

export type Customer = {
  id: number;
  display_name: string;
  contact_name: string | null;
  business_name: string | null;
  email: string | null;
  phone: string | null;
  is_active: boolean;
  created_at: string;
};

type CustomerListResponse = {
  total: number;
  customers: Customer[];
};

export async function listCustomers(token: string, isActive = true) {
  const query = new URLSearchParams({
    limit: "200",
    offset: "0",
    is_active: String(isActive),
  }).toString();
  return apiRequest<CustomerListResponse>(`/customers?${query}`, "GET", token);
}
