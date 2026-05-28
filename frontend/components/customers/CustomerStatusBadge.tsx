import { Badge } from "@/components/ui/badge";

interface CustomerStatusBadgeProps {
  status: "invited" | "active";
}

const config = {
  invited: { label: "Invitado", variant: "secondary" as const },
  active: { label: "Activo", variant: "default" as const },
};

export function CustomerStatusBadge({ status }: CustomerStatusBadgeProps) {
  const { label, variant } = config[status];
  return <Badge variant={variant}>{label}</Badge>;
}
