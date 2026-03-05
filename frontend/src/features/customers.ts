import { apiRequest } from "../lib/api";

export type Customer = {
  id: number;
  display_name: string;
  contact_name: string | null;
  business_name: string | null;
  email: string | null;
  phone: string | null;
  address: string | null;
  city: string | null;
  state: string | null;
  zip_code: string | null;
  is_active: boolean;
  created_at: string;
};

type CustomerListResponse = {
  total: number;
  customers: Customer[];
};

export async function listCustomers(token: string, options?: { isActive?: boolean; search?: string }) {
  const params = new URLSearchParams({
    limit: "200",
    offset: "0",
  });
  if (options?.isActive !== undefined) {
    params.set("is_active", String(options.isActive));
  }
  if (options?.search && options.search.trim()) {
    params.set("search", options.search.trim());
  }
  return apiRequest<CustomerListResponse>(`/customers?${params.toString()}`, "GET", token);
}

export type CustomerCreatePayload = {
  display_name: string;
  contact_name?: string | null;
  business_name?: string | null;
  email?: string | null;
  phone?: string | null;
  is_active?: boolean;
  address?: string | null;
  city?: string | null;
  state?: string | null;
  zip_code?: string | null;
};

export type CustomerUpdatePayload = {
  display_name?: string;
  contact_name?: string | null;
  business_name?: string | null;
  email?: string | null;
  phone?: string | null;
  is_active?: boolean;
  address?: string | null;
  city?: string | null;
  state?: string | null;
  zip_code?: string | null;
};

export async function createCustomer(token: string, payload: CustomerCreatePayload) {
  return apiRequest<Customer>("/customers", "POST", token, payload);
}

export async function updateCustomer(token: string, id: number, payload: CustomerUpdatePayload) {
  return apiRequest<Customer>(`/customers/${id}`, "PATCH", token, payload);
}

export async function deleteCustomer(token: string, id: number) {
  return apiRequest<void>(`/customers/${id}`, "DELETE", token);
}
