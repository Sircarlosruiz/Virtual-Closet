"use client";

import { Smartphone, QrCode } from "lucide-react";

interface MethodSelectorProps {
  onSelect: (method: "totp" | "sms") => void;
}

export function MethodSelector({ onSelect }: MethodSelectorProps) {
  const cardBase =
    "flex flex-col items-center gap-3 p-6 rounded-2xl border-2 cursor-pointer transition-all hover:scale-[1.02] active:scale-[0.98]";

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-xl font-bold text-gray-900 text-center">
        Elegí tu método de verificación
      </h2>
      <p className="text-sm text-gray-500 text-center mb-2">
        Ambos métodos protegen tu cuenta con un segundo factor de seguridad.
      </p>

      <div className="flex flex-col sm:flex-row gap-4">
        {/* TOTP Option */}
        <button
          type="button"
          onClick={() => onSelect("totp")}
          className={`${cardBase} flex-1 border-indigo-200 hover:border-indigo-400 hover:bg-indigo-50`}
        >
          <div className="h-12 w-12 rounded-xl bg-indigo-100 flex items-center justify-center">
            <QrCode className="h-6 w-6 text-indigo-600" />
          </div>
          <div className="text-center">
            <p className="font-semibold text-gray-900">App Autenticadora</p>
            <p className="text-xs text-gray-500 mt-1">Google Authenticator, Authy, etc.</p>
          </div>
          <span className="text-xs font-medium text-indigo-600 bg-indigo-100 px-2 py-0.5 rounded-full">
            Recomendado
          </span>
        </button>

        {/* SMS Option */}
        <button
          type="button"
          onClick={() => onSelect("sms")}
          className={`${cardBase} flex-1 border-gray-200 hover:border-gray-400 hover:bg-gray-50`}
        >
          <div className="h-12 w-12 rounded-xl bg-gray-100 flex items-center justify-center">
            <Smartphone className="h-6 w-6 text-gray-600" />
          </div>
          <div className="text-center">
            <p className="font-semibold text-gray-900">SMS</p>
            <p className="text-xs text-gray-500 mt-1">Código por mensaje de texto</p>
          </div>
        </button>
      </div>
    </div>
  );
}
