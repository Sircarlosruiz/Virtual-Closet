"use client";

import { useState } from "react";
import { useBuyerLinks, useGenerateBuyerLink } from "@/hooks/useSettings";
import { usePortalCatalogsList } from "@/hooks/usePortal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, Copy, Check, Link2, Calendar } from "lucide-react";

export function BuyerLinkGenerator() {
  const { data: catalogsData, isLoading: catalogsLoading } = usePortalCatalogsList(1, 50);
  const { data: linksData, isLoading: linksLoading } = useBuyerLinks();
  const generateMutation = useGenerateBuyerLink();

  const [selectedCatalogs, setSelectedCatalogs] = useState<Set<string>>(new Set());
  const [ttlDays, setTtlDays] = useState(30);
  const [generatedUrl, setGeneratedUrl] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const catalogs = catalogsData?.catalogs ?? [];
  const links = linksData?.links ?? [];

  const handleGenerate = async () => {
    if (selectedCatalogs.size === 0) return;

    const result = await generateMutation.mutateAsync({
      catalog_ids: Array.from(selectedCatalogs),
      ttl_days: ttlDays,
    });

    setGeneratedUrl(result.signed_url);
    setCopied(false);
  };

  const handleCopy = async () => {
    if (!generatedUrl) return;
    await navigator.clipboard.writeText(generatedUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const toggleCatalog = (id: string) => {
    const next = new Set(selectedCatalogs);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedCatalogs(next);
  };

  const selectAll = () => {
    setSelectedCatalogs(new Set(catalogs.map((c) => c.id)));
  };

  const clearAll = () => {
    setSelectedCatalogs(new Set());
  };

  return (
    <div className="space-y-8">
      {/* Generator form */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-zinc-900">Generar nuevo enlace</h3>

        {/* Catalog selection */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label>Catálogos</Label>
            <div className="flex gap-2 text-xs">
              <button
                type="button"
                onClick={selectAll}
                className="text-indigo-600 hover:text-indigo-700"
              >
                Seleccionar todos
              </button>
              <span className="text-zinc-300">|</span>
              <button
                type="button"
                onClick={clearAll}
                className="text-zinc-500 hover:text-zinc-700"
              >
                Limpiar
              </button>
            </div>
          </div>

          {catalogsLoading ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-4 w-4 animate-spin text-zinc-400" />
            </div>
          ) : catalogs.length === 0 ? (
            <div className="text-center py-4 border rounded-lg bg-zinc-50">
              <p className="text-sm text-zinc-500">
                No hay catálogos.{" "}
                <a href="/dashboard/catalogos" className="text-indigo-600 hover:underline">
                  Creá uno primero
                </a>
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto border rounded-lg p-3">
              {catalogs.map((catalog) => (
                <label
                  key={catalog.id}
                  className="flex items-center gap-2 p-2 rounded-lg hover:bg-zinc-50 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={selectedCatalogs.has(catalog.id)}
                    onChange={() => toggleCatalog(catalog.id)}
                    className="h-4 w-4 rounded border-zinc-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <span className="text-sm truncate">{catalog.name}</span>
                </label>
              ))}
            </div>
          )}
          <p className="text-xs text-zinc-500">
            {selectedCatalogs.size} catálogo(s) seleccionado(s)
          </p>
        </div>

        {/* TTL */}
        <div className="space-y-2">
          <Label htmlFor="ttl">Duración (días)</Label>
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-zinc-400" />
            <Input
              id="ttl"
              type="number"
              min={1}
              max={365}
              value={ttlDays}
              onChange={(e) => setTtlDays(parseInt(e.target.value, 10) || 30)}
              className="w-32"
            />
          </div>
        </div>

        {/* Generate button */}
        <Button
          onClick={handleGenerate}
          disabled={generateMutation.isPending || selectedCatalogs.size === 0}
          className="bg-indigo-600 hover:bg-indigo-700"
        >
          {generateMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Link2 className="h-4 w-4" />
          )}
          Generar enlace
        </Button>

        {/* Generated URL */}
        {generatedUrl && (
          <div className="space-y-2 p-4 bg-green-50 border border-green-200 rounded-xl">
            <p className="text-sm font-medium text-green-800">Enlace generado:</p>
            <div className="flex items-center gap-2">
              <Input
                readOnly
                value={generatedUrl}
                className="flex-1 font-mono text-xs bg-white"
              />
              <Button
                size="sm"
                variant="outline"
                onClick={handleCopy}
                className="shrink-0"
              >
                {copied ? (
                  <Check className="h-4 w-4 text-green-600" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Link history */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-zinc-900">Enlaces generados</h3>

        {linksLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
          </div>
        ) : links.length === 0 ? (
          <div className="text-center py-8 border rounded-xl bg-zinc-50">
            <Link2 className="h-8 w-8 text-zinc-400 mx-auto mb-2" />
            <p className="text-sm text-zinc-500">No hay enlaces generados</p>
          </div>
        ) : (
          <div className="border rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-zinc-50 border-b">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-zinc-600">Creado</th>
                  <th className="text-left px-4 py-3 font-medium text-zinc-600">Expira</th>
                  <th className="text-left px-4 py-3 font-medium text-zinc-600">Catálogos</th>
                  <th className="text-right px-4 py-3 font-medium text-zinc-600">Acción</th>
                </tr>
              </thead>
              <tbody>
                {links.map((link) => {
                  const isExpired = new Date(link.expires_at) < new Date();
                  return (
                    <tr
                      key={link.id}
                      className={`border-b last:border-0 ${
                        isExpired ? "opacity-50" : "hover:bg-zinc-50"
                      }`}
                    >
                      <td className="px-4 py-3 text-zinc-500">
                        {new Date(link.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                            isExpired
                              ? "bg-red-100 text-red-700"
                              : "bg-green-100 text-green-700"
                          }`}
                        >
                          {isExpired ? "Expirado" : "Activo"}
                        </span>
                        <span className="ml-2 text-xs text-zinc-400">
                          {new Date(link.expires_at).toLocaleDateString()}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-zinc-500">
                        {link.catalog_ids.length} catálogo(s)
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={async () => {
                            await navigator.clipboard.writeText(link.signed_url);
                          }}
                          className="h-8 w-8 p-0"
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
