"use client";

import { useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { Copy, Check, Shield } from "lucide-react";
import { OtpInput } from "./otp-input";

interface TotpSetupStepProps {
  otpauthUri: string;
  secret: string;
  onConfirm: (otpCode: string) => Promise<void>;
  onBack: () => void;
}

export function TotpSetupStep({ otpauthUri, secret, onConfirm, onBack }: TotpSetupStepProps) {
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(secret);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleComplete = async (code: string) => {
    setError(null);
    setSubmitting(true);
    try {
      await onConfirm(code);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Código inválido. Intentá de nuevo.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col items-center gap-6">
      <div className="text-center">
        <h2 className="text-xl font-bold text-gray-900">Escaneá el código QR</h2>
        <p className="text-sm text-gray-500 mt-1">
          Abrí tu app autenticadora y escaneá el código de abajo.
        </p>
      </div>

      {/* QR Code */}
      <div className="p-4 bg-white rounded-2xl border-2 border-gray-200">
        <QRCodeSVG value={otpauthUri} size={200} level="M" />
      </div>

      {/* Manual entry */}
      <div className="w-full">
        <p className="text-sm font-medium text-gray-700 mb-2">
          ¿No podés escanear? Ingresá esta clave manualmente:
        </p>
        <div className="flex items-center gap-2 p-3 bg-gray-50 rounded-xl border border-gray-200">
          <code className="flex-1 font-mono text-sm text-gray-800 tracking-wider break-all">
            {secret}
          </code>
          <button
            type="button"
            onClick={handleCopy}
            className="p-2 rounded-lg hover:bg-gray-200 transition-colors"
            title="Copiar clave"
          >
            {copied ? (
              <Check className="h-4 w-4 text-green-600" />
            ) : (
              <Copy className="h-4 w-4 text-gray-500" />
            )}
          </button>
        </div>
      </div>

      {/* Confirmation */}
      <div className="w-full flex flex-col items-center gap-3">
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <Shield className="h-4 w-4" />
          <span>Ingresá el código de 6 dígitos para confirmar:</span>
        </div>
        <OtpInput
          onComplete={handleComplete}
          disabled={submitting}
          error={error || undefined}
          autoFocus
        />
      </div>

      <button
        type="button"
        onClick={onBack}
        className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
      >
        ← Volver
      </button>
    </div>
  );
}
