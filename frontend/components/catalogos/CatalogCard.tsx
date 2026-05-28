"use client";

import Link from "next/link";
import { Catalogo } from "@/lib/api/catalogos";
import { StatusBadge } from "./StatusBadge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface CatalogCardProps {
  catalogo: Catalogo;
}

export function CatalogCard({ catalogo }: CatalogCardProps) {
  const updatedDate = new Date(catalogo.updated_at).toLocaleDateString("es-ES", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

  return (
    <Link href={`/dashboard/catalogos/${catalogo.id}`}>
      <Card className="hover:shadow-md transition-shadow cursor-pointer">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg truncate">{catalogo.name}</CardTitle>
            <StatusBadge status={catalogo.status} />
          </div>
          <CardDescription>
            {catalogo.item_count} {catalogo.item_count === 1 ? "prenda" : "prendas"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">Actualizado: {updatedDate}</p>
        </CardContent>
      </Card>
    </Link>
  );
}
