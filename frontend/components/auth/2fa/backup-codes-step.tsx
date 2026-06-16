"use client";

import { useState } from "react";
import { Copy, Check, ShieldAlert } from "lucide-react";

interface BackupCodesStepProps {
  codes: string[];
  onContinue: () => void;
}

export function BackupCodesStep({ codes, onContinue }: BackupCodesStepProps) {
  const [copied, setCopied] = useState(false);
  const [acknowledged, setAcknowledged] = useState(false);

  const handleCopyAll = async () => {
    await navigator.clipboard.writeText(codes.join("\n"));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex flex-col items-center gap-6">
      <div className="text-center">
        <div className="mx-auto h-12 w-12 rounded-full bg-amber-100 flex items-center justify-center mb-3">
          <ShieldAlert className="h-6 w-6 text-amber-600" />
        </div>
        <h2 className="text-xl font-bold text-gray-900">Guardá tus códigos de respaldo</h2>
        <p className="text-sm text-gray-500 mt-1">
          Estos códigos te permiten acceder si perdés tu dispositivo. Guardalos en un lugar seguro.
        </p>
      </div>

      {/* Backup codes grid */}
      <div className="w-full">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Códigos de respaldo</span>
          <button
            type="button"
            onClick={handleCopyAll}
            className="flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-700 transition-colors"
          >
            {copied ? (
              <>
                <Check className="h-3 w-3" />
                Copiado
              </>
            ) : (
              <>
                <Copy className="h-3 w-3" />
                Copiar todos
              </>
            )}
          </button>
        </div>

        <div className="grid grid-cols-2 gap-2 p-4 bg-gray-50 rounded-xl border border-gray-200">
          {codes.map((code, index) => (
            <code
              key={index}
              className="font-mono text-sm text-gray-800 bg-white px-3 py-2 rounded-lg border border-gray-100 text-center"
            >
              {code}
            </code>
          ))}
        </div>
      </div>

      {/* Acknowledgment */}
      <label className="flex items-start gap-3 cursor-pointer w-full">
        <input
          type="checkbox"
          checked={acknowledged}
          onChange={(e) => setAcknowledged(e.target.checked)}
          className="mt-1 h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
        />
        <span className="text-sm text-gray-700">
          Guardé estos códigos en un lugar seguro. Entiendo que no podré verlos de nuevo.
        </span>
      </label>

      {/* Continue button */}
      <button
        type="button"
        onClick={onContinue}
        disabled={!acknowledged}
        className="h-12 w-full rounded-full text-base font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
        style={{ background: "#6366F1", boxShadow: "0 4px 14px rgba(99,102,241,.32)" }}
      >
        Continuar al dashboard
      </button>
    </div>
  );
}
