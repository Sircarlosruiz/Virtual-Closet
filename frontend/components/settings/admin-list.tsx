"use client";

import { useState } from "react";
import { useAdminList, useInviteAdmin, useRevokeAdmin } from "@/hooks/useSettings";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader2, Plus, Trash2, Mail, Clock } from "lucide-react";

export function AdminList() {
  const { data, isLoading } = useAdminList();
  const inviteMutation = useInviteAdmin();
  const revokeMutation = useRevokeAdmin();
  const [email, setEmail] = useState("");
  const [revokeId, setRevokeId] = useState<string | null>(null);
  const [revokeEmail, setRevokeEmail] = useState("");

  const handleInvite = async () => {
    if (!email.trim()) return;
    await inviteMutation.mutateAsync(email.trim());
    setEmail("");
  };

  const handleRevoke = async () => {
    if (!revokeId) return;
    await revokeMutation.mutateAsync(revokeId);
    setRevokeId(null);
    setRevokeEmail("");
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
      </div>
    );
  }

  const admins = data?.admins ?? [];

  return (
    <div className="space-y-6">
      {/* Invite form */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex-1">
          <Input
            type="email"
            placeholder="Email del nuevo admin"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleInvite();
            }}
          />
        </div>
        <Button
          onClick={handleInvite}
          disabled={inviteMutation.isPending || !email.trim()}
          className="bg-indigo-600 hover:bg-indigo-700"
        >
          {inviteMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Plus className="h-4 w-4" />
          )}
          Invitar admin
        </Button>
      </div>

      {/* Admin list */}
      {admins.length === 0 ? (
        <div className="text-center py-8 border rounded-xl bg-zinc-50">
          <Mail className="h-8 w-8 text-zinc-400 mx-auto mb-2" />
          <p className="text-sm text-zinc-500">No hay admins en este tenant</p>
        </div>
      ) : (
        <div className="border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-zinc-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-zinc-600">Email</th>
                <th className="text-left px-4 py-3 font-medium text-zinc-600">Rol</th>
                <th className="text-left px-4 py-3 font-medium text-zinc-600">Estado</th>
                <th className="text-right px-4 py-3 font-medium text-zinc-600">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {admins.map((admin) => (
                <tr key={admin.id} className="border-b last:border-0 hover:bg-zinc-50">
                  <td className="px-4 py-3 font-mono text-xs">{admin.email}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                        admin.role === "owner"
                          ? "bg-indigo-100 text-indigo-700"
                          : admin.role === "admin"
                            ? "bg-zinc-100 text-zinc-700"
                            : "bg-yellow-100 text-yellow-700"
                      }`}
                    >
                      {admin.role === "pending" && <Clock className="h-3 w-3" />}
                      {admin.role}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-zinc-500">
                    {new Date(admin.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {admin.role !== "owner" && (
                      <AlertDialog>
                        <AlertDialogTrigger>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-red-600 hover:text-red-700 hover:bg-red-50 h-8 w-8 p-0"
                            onClick={() => {
                              setRevokeId(admin.id);
                              setRevokeEmail(admin.email);
                            }}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Revocar acceso</AlertDialogTitle>
                            <AlertDialogDescription>
                              ¿Estás seguro de que querés revocar el acceso de{" "}
                              <span className="font-mono font-medium">{revokeEmail}</span>?
                              Esta acción no se puede deshacer.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancelar</AlertDialogCancel>
                            <AlertDialogAction
                              onClick={handleRevoke}
                              className="bg-red-600 hover:bg-red-700"
                              disabled={revokeMutation.isPending}
                            >
                              {revokeMutation.isPending ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                "Revocar"
                              )}
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
