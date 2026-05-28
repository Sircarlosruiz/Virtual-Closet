"use client";

import { useState } from "react";
import { useCustomersList } from "@/hooks/useCustomers";
import { CustomerStatusBadge } from "@/components/customers/CustomerStatusBadge";
import { RegisterCustomerModal } from "@/components/customers/RegisterCustomerModal";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";

export default function CustomersPage() {
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const { data, isLoading, error } = useCustomersList(1, 50);

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
            Clientes
          </h1>
          <Button disabled>
            <Plus className="w-4 h-4 mr-2" />
            Registrar cliente
          </Button>
        </div>
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="h-16 bg-zinc-200 dark:bg-zinc-800 rounded-lg animate-pulse"
            />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto py-8">
        <div className="text-center py-12">
          <p className="text-red-600">Error al cargar clientes</p>
          <p className="text-sm text-muted-foreground mt-2">{error.message}</p>
        </div>
      </div>
    );
  }

  const customers = data?.customers ?? [];

  return (
    <div className="max-w-4xl mx-auto py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
          Clientes
        </h1>
        <Button onClick={() => setShowRegisterModal(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Registrar cliente
        </Button>
      </div>

      {customers.length === 0 ? (
        <div className="text-center py-12 border-2 border-dashed rounded-lg">
          <p className="text-lg font-medium text-zinc-700 dark:text-zinc-300">
            No tienes clientes aún
          </p>
          <p className="text-sm text-muted-foreground mt-2 mb-4">
            Registra tu primer cliente para darle acceso al portal
          </p>
          <Button onClick={() => setShowRegisterModal(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Registrar tu primer cliente
          </Button>
        </div>
      ) : (
        <div className="bg-white dark:bg-zinc-900 rounded-lg border overflow-hidden">
          <table className="w-full">
            <thead className="bg-zinc-50 dark:bg-zinc-800 border-b">
              <tr>
                <th className="text-left px-4 py-3 text-sm font-medium text-zinc-500">
                  Nombre
                </th>
                <th className="text-left px-4 py-3 text-sm font-medium text-zinc-500">
                  Email
                </th>
                <th className="text-left px-4 py-3 text-sm font-medium text-zinc-500">
                  Estado
                </th>
                <th className="text-left px-4 py-3 text-sm font-medium text-zinc-500">
                  Registrado
                </th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {customers.map((customer) => {
                const registeredDate = new Date(customer.created_at).toLocaleDateString("es-ES", {
                  day: "numeric",
                  month: "short",
                  year: "numeric",
                });
                return (
                  <tr key={customer.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-800/50">
                    <td className="px-4 py-3 text-sm font-medium text-zinc-900 dark:text-zinc-50">
                      {customer.name}
                    </td>
                    <td className="px-4 py-3 text-sm text-zinc-600 dark:text-zinc-400">
                      {customer.email}
                    </td>
                    <td className="px-4 py-3">
                      <CustomerStatusBadge status={customer.status} />
                    </td>
                    <td className="px-4 py-3 text-sm text-zinc-500">
                      {registeredDate}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <RegisterCustomerModal
        open={showRegisterModal}
        onOpenChange={setShowRegisterModal}
      />
    </div>
  );
}
