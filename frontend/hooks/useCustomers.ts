"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getCustomers,
  registerCustomer,
  type CustomerListResponse,
  type RegisterCustomerInput,
} from "@/lib/api/customers";
import { toast } from "sonner";

const CUSTOMERS_KEY = ["customers"];

export function useCustomersList(page = 1, pageSize = 20) {
  return useQuery<CustomerListResponse>({
    queryKey: [...CUSTOMERS_KEY, page, pageSize],
    queryFn: () => getCustomers(page, pageSize),
  });
}

export function useRegisterCustomer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: RegisterCustomerInput) => registerCustomer(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CUSTOMERS_KEY });
      toast.success("Cliente registrado. Se ha enviado un correo de invitación.");
    },
    onError: (err: Error) => {
      if (err.message.includes("already exists")) {
        toast.error("Este email ya está registrado");
      } else {
        toast.error(`Error al registrar cliente: ${err.message}`);
      }
    },
  });
}
