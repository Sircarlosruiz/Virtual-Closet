"use client";

import { PortalCatalogItem } from "@/lib/api/portal";
import { formatPrice } from "@/lib/utils";

interface PortalCatalogItemCardProps {
  item: PortalCatalogItem;
}

export function PortalCatalogItemCard({ item }: PortalCatalogItemCardProps) {
  return (
    <div className="bg-white dark:bg-zinc-900 rounded-lg border overflow-hidden">
      <div className="relative aspect-square bg-zinc-100 dark:bg-zinc-800">
        <img
          src={item.image_url}
          alt={item.garment_name}
          className="w-full h-full object-cover"
        />
      </div>
      <div className="p-3">
        <h4 className="text-sm font-medium truncate">{item.garment_name}</h4>
        <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-50 mt-1">
          ${formatPrice(item.price)}
        </p>
        <p className="text-xs text-muted-foreground mt-1">SKU: {item.sku}</p>
      </div>
    </div>
  );
}
