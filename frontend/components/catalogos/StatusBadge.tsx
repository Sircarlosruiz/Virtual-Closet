import { Badge } from "@/components/ui/badge";

interface StatusBadgeProps {
  status: "draft" | "published";
}

const config = {
  draft: { label: "Borrador", variant: "secondary" as const },
  published: { label: "Publicado", variant: "default" as const },
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const { label, variant } = config[status];
  return <Badge variant={variant}>{label}</Badge>;
}
