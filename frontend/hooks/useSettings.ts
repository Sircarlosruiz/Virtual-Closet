"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  validateBuyerLink,
  generateBuyerLink,
  listBuyerLinks,
  getTenant,
  listAdmins,
  inviteAdmin,
  revokeAdmin,
  type ValidateLinkResponse,
  type BuyerLinkRequest,
  type BuyerLinkResponse,
  type BuyerLinkListResponse,
  type AdminListResponse,
  type TenantResponse,
} from "@/lib/api/settings";

export function useValidateBuyerLink(token: string | null) {
  return useQuery<ValidateLinkResponse>({
    queryKey: ["buyer-link", "validate", token],
    queryFn: () => validateBuyerLink(token!),
    enabled: !!token,
    retry: false,
  });
}

export function useTenant() {
  return useQuery<TenantResponse>({
    queryKey: ["tenant", "me"],
    queryFn: getTenant,
    retry: false,
  });
}

export function useAdminList() {
  return useQuery<AdminListResponse>({
    queryKey: ["admins"],
    queryFn: listAdmins,
    retry: false,
  });
}

export function useInviteAdmin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (email: string) => inviteAdmin(email),
    onSuccess: () => {
      toast.success("Invitación enviada exitosamente");
      queryClient.invalidateQueries({ queryKey: ["admins"] });
    },
    onError: (err: Error) => {
      if (err.message.includes("409") || err.message.includes("pendiente")) {
        toast.error("Ya hay una invitación pendiente para este email");
      } else if (err.message.includes("429")) {
        toast.error("Se alcanzó el máximo de invitaciones");
      } else {
        toast.error(`Error: ${err.message}`);
      }
    },
  });
}

export function useRevokeAdmin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (adminId: string) => revokeAdmin(adminId),
    onSuccess: () => {
      toast.success("Admin revocado exitosamente");
      queryClient.invalidateQueries({ queryKey: ["admins"] });
    },
    onError: (err: Error) => {
      if (err.message.includes("403")) {
        toast.error("No podés revocar este admin");
      } else {
        toast.error(`Error: ${err.message}`);
      }
    },
  });
}

export function useBuyerLinks() {
  return useQuery<BuyerLinkListResponse>({
    queryKey: ["buyer-links"],
    queryFn: listBuyerLinks,
    retry: false,
  });
}

export function useGenerateBuyerLink() {
  const queryClient = useQueryClient();

  return useMutation<BuyerLinkResponse, Error, BuyerLinkRequest>({
    mutationFn: (body) => generateBuyerLink(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["buyer-links"] });
    },
    onError: (err: Error) => {
      toast.error(`Error: ${err.message}`);
    },
  });
}
