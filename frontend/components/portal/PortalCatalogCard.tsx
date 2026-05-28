"use client";

import Link from "next/link";
import { PortalCatalog } from "@/lib/api/portal";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface PortalCatalogCardProps {
  catalog: PortalCatalog;
}

export function PortalCatalogCard({ catalog }: PortalCatalogCardProps) {
  const createdDate = new Date(catalog.created_at).toLocaleDateString("es-ES", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

  return (
    <Link href={`/portal/catalogs/${catalog.id}`}>
      <Card className="hover:shadow-md transition-shadow cursor-pointer">
        <CardHeader>
          <CardTitle className="text-lg">{catalog.name}</CardTitle>
          <CardDescription>
            {catalog.item_count} {catalog.item_count === 1 ? "prenda" : "prendas"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">Publicado: {createdDate}</p>
        </CardContent>
      </Card>
    </Link>
  );
}
