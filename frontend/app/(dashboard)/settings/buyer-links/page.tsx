"use client";

import { BuyerLinkGenerator } from "@/components/settings/buyer-link-generator";

export default function BuyerLinksSettingsPage() {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-lg font-semibold text-zinc-900">Enlaces de acceso para compradores</h2>
        <p className="text-sm text-zinc-500 mt-1">
          Generá enlaces compartibles para que los compradores accedan a tus catálogos sin necesidad de crear una cuenta.
        </p>
      </div>

      <BuyerLinkGenerator />
    </div>
  );
}
