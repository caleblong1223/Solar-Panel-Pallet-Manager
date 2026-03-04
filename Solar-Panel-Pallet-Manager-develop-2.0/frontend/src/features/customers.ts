import { apiRequest } from "../lib/api";

export type Customer = {
  id: number;
  display_name: string;
  contact_name: string | null;
  business_name: string | null;
  email: string | null;
  phone: string | null;
  is_active: boolean;
};

type CustomerListResponse = {
  total: number;
  customers: Customer[];
};

export async function listCustomers(token: string, onlyActive = true) {
  const params = new URLSearchParams({
    limit: "200",
    offset: "0",
  });
  if (onlyActive) {
    params.set("is_active", "true");
  }
  return apiRequest<CustomerListResponse>(`/customers?${params.toString()}`, "GET", token);
}

