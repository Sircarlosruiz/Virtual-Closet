"use client";

import { useState } from "react";
import { Phone } from "lucide-react";
import { OtpInput } from "./otp-input";

interface SmsSetupStepProps {
  onSendOtp: (phoneNumber: string) => Promise<void>;
  onConfirm: (otpCode: string) => Promise<void>;
  onBack: () => void;
}

export function SmsSetupStep({ onSendOtp, onConfirm, onBack }: SmsSetupStepProps) {
  const [phone, setPhone] = useState("");
  const [phoneError, setPhoneError] = useState<string | null>(null);
  const [otpSent, setOtpSent] = useState(false);
  const [otpError, setOtpError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const validatePhone = (value: string): string | null => {
    const cleaned = value.replace(/[\s\-\(\)]/g, "");
    if (!cleaned) return "El número de teléfono es obligatorio";
    if (!/^\+\d{7,15}$/.test(cleaned)) return "Formato inválido. Usá el formato internacional (ej: +50588881234)";
    return null;
  };

  const handleSend = async () => {
    const error = validatePhone(phone);
    if (error) {
      setPhoneError(error);
      return;
    }
    setPhoneError(null);
    setSubmitting(true);
    try {
      await onSendOtp(phone.replace(/[\s\-\(\)]/g, ""));
      setOtpSent(true);
    } catch (err) {
      if (err instanceof Error) {
        setPhoneError(err.message);
      } else {
        setPhoneError("No se pudo enviar el SMS. Intentá de nuevo.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleOtpComplete = async (code: string) => {
    setOtpError(null);
    setSubmitting(true);
    try {
      await onConfirm(code);
    } catch (err) {
      if (err instanceof Error) {
        setOtpError(err.message);
      } else {
        setOtpError("Código inválido. Intentá de nuevo.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const inputClass =
    "h-12 w-full rounded-xl border px-4 text-base outline-none transition-all " +
    "focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 " +
    "placeholder:text-gray-400 " +
    (phoneError ? "border-red-400 bg-red-50" : "border-gray-200");

  if (otpSent) {
    return (
      <div className="flex flex-col items-center gap-6">
        <div className="text-center">
          <h2 className="text-xl font-bold text-gray-900">Verificá tu teléfono</h2>
          <p className="text-sm text-gray-500 mt-1">
            Enviamos un código de 6 dígitos a tu número.
          </p>
        </div>

        <div className="flex items-center gap-2 p-3 bg-indigo-50 rounded-xl">
          <Phone className="h-4 w-4 text-indigo-600" />
          <span className="text-sm font-medium text-indigo-700">{phone}</span>
        </div>

        <OtpInput
          onComplete={handleOtpComplete}
          disabled={submitting}
          error={otpError || undefined}
          autoFocus
          autocomplete="one-time-code"
        />

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

  return (
    <div className="flex flex-col items-center gap-6">
      <div className="text-center">
        <h2 className="text-xl font-bold text-gray-900">Configurá verificación por SMS</h2>
        <p className="text-sm text-gray-500 mt-1">
          Ingresá tu número de teléfono para recibir un código de verificación.
        </p>
      </div>

      <div className="w-full flex flex-col gap-3">
        <label htmlFor="phone" className="text-sm font-semibold text-gray-800">
          Número de teléfono
        </label>
        <input
          id="phone"
          type="tel"
          placeholder="+50588881234"
          value={phone}
          onChange={(e) => {
            setPhone(e.target.value);
            setPhoneError(null);
          }}
          className={inputClass}
          autoComplete="tel"
        />
        {phoneError && <p className="text-xs text-red-500">{phoneError}</p>}
        <p className="text-xs text-gray-400">
          Formato internacional: +código-país + número
        </p>
      </div>

      <button
        type="button"
        onClick={handleSend}
        disabled={submitting || !phone.trim()}
        className="h-12 w-full rounded-full text-base font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
        style={{ background: "#6366F1", boxShadow: "0 4px 14px rgba(99,102,241,.32)" }}
      >
        {submitting ? "Enviando..." : "Enviar código"}
      </button>

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
