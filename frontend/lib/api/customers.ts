import { apiFetch } from "@/lib/api";

export interface Customer {
  id: string;
  name: string;
  email: string;
  status: "invited" | "active";
  created_at: string;
}

export interface CustomerListResponse {
  customers: Customer[];
  total: number;
  page: number;
  page_size: number;
}

export interface RegisterCustomerInput {
  name: string;
  email: string;
}

export async function getCustomers(
  page = 1,
  pageSize = 20
): Promise<CustomerListResponse> {
  return apiFetch(`/api/customers?page=${page}&page_size=${pageSize}`);
}

export async function registerCustomer(
  input: RegisterCustomerInput
): Promise<Customer> {
  return apiFetch("/api/customers", {
    method: "POST",
    body: JSON.stringify(input),
  });
}
