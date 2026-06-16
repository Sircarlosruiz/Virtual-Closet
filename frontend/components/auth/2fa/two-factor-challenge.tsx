"use client";

import { useState, useCallback } from "react";
import { Shield, Smartphone, KeyRound } from "lucide-react";
import { OtpInput } from "./otp-input";
import { SmsResendTimer } from "./sms-resend-timer";
import { apiFetchWithChallenge } from "@/lib/auth/challenge-context";

type ChallengeMode = "totp" | "sms" | "backup";

interface TwoFactorChallengeProps {
  onSuccess: () => void;
  userMethod?: "totp" | "sms";
  phoneMasked?: string;
}

export function TwoFactorChallenge({ onSuccess, userMethod, phoneMasked }: TwoFactorChallengeProps) {
  const [mode, setMode] = useState<ChallengeMode>(userMethod || "totp");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [backupCode, setBackupCode] = useState("");

  const handleOtpComplete = useCallback(async (code: string) => {
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "totp") {
        await apiFetchWithChallenge("/api/auth/2fa/challenge", {
          method: "POST",
          body: JSON.stringify({ otp_code: code }),
        });
      } else if (mode === "sms") {
        await apiFetchWithChallenge("/api/auth/2fa/sms/verify", {
          method: "POST",
          body: JSON.stringify({ otp_code: code }),
        });
      }
      onSuccess();
    } catch (err) {
      if (err instanceof Error && "status" in err) {
        const httpErr = err as Error & { status?: number };
        if (httpErr.status === 429) {
          setError("Demasiados intentos. Iniciá sesión de nuevo.");
        } else {
          setError(err.message);
        }
      } else {
        setError("Código incorrecto, intentá de nuevo.");
      }
    } finally {
      setSubmitting(false);
    }
  }, [mode, onSuccess]);

  const handleBackupSubmit = useCallback(async () => {
    if (!backupCode.trim()) return;
    setError(null);
    setSubmitting(true);
    try {
      await apiFetchWithChallenge("/api/auth/2fa/challenge", {
        method: "POST",
        body: JSON.stringify({ backup_code: backupCode.trim() }),
      });
      onSuccess();
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Código de respaldo inválido.");
      }
    } finally {
      setSubmitting(false);
    }
  }, [backupCode, onSuccess]);

  const handleSmsResend = useCallback(async () => {
    await apiFetchWithChallenge("/api/auth/2fa/sms/send", {
      method: "POST",
    });
  }, []);

  const inputClass =
    "h-12 w-full rounded-xl border px-4 text-base outline-none transition-all " +
    "focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 " +
    "placeholder:text-gray-400 " +
    (error ? "border-red-400 bg-red-50" : "border-gray-200");

  return (
    <div className="flex flex-col items-center gap-6">
      {/* Header */}
      <div className="text-center">
        <div className="mx-auto h-12 w-12 rounded-full bg-indigo-100 flex items-center justify-center mb-3">
          <Shield className="h-6 w-6 text-indigo-600" />
        </div>
        <h2 className="text-xl font-bold text-gray-900">Verificación en dos pasos</h2>
        {mode === "sms" && phoneMasked && (
          <p className="text-sm text-gray-500 mt-1">
            Enviamos un código a <span className="font-medium text-gray-700">{phoneMasked}</span>
          </p>
        )}
        {mode === "totp" && (
          <p className="text-sm text-gray-500 mt-1">
            Ingresá el código de tu app autenticadora.
          </p>
        )}
      </div>

      {/* OTP Input */}
      {mode !== "backup" && (
        <OtpInput
          onComplete={handleOtpComplete}
          disabled={submitting}
          error={error || undefined}
          autoFocus
          autocomplete={mode === "sms" ? "one-time-code" : undefined}
        />
      )}

      {/* Backup code input */}
      {mode === "backup" && (
        <div className="w-full flex flex-col gap-3">
          <label htmlFor="backup-code" className="text-sm font-semibold text-gray-800">
            Código de respaldo
          </label>
          <input
            id="backup-code"
            type="text"
            placeholder="Ingresá uno de tus 8 códigos"
            value={backupCode}
            onChange={(e) => setBackupCode(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleBackupSubmit();
            }}
            className={inputClass}
            autoComplete="off"
          />
          {error && <p className="text-xs text-red-500">{error}</p>}
          <button
            type="button"
            onClick={handleBackupSubmit}
            disabled={submitting || !backupCode.trim()}
            className="h-12 w-full rounded-full text-base font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
            style={{ background: "#6366F1", boxShadow: "0 4px 14px rgba(99,102,241,.32)" }}
          >
            {submitting ? "Verificando..." : "Verificar"}
          </button>
        </div>
      )}

      {/* SMS resend */}
      {mode === "sms" && (
        <SmsResendTimer onResend={handleSmsResend} initialCooldown={30} />
      )}

      {/* Method toggle */}
      {mode !== "backup" && (
        <div className="flex items-center gap-4 text-sm">
          {mode === "totp" && (
            <button
              type="button"
              onClick={() => {
                setMode("sms");
                setError(null);
              }}
              className="flex items-center gap-1.5 text-indigo-600 hover:text-indigo-700 font-medium"
            >
              <Smartphone className="h-4 w-4" />
              Usar SMS
            </button>
          )}
          {mode === "sms" && (
            <button
              type="button"
              onClick={() => {
                setMode("totp");
                setError(null);
              }}
              className="flex items-center gap-1.5 text-indigo-600 hover:text-indigo-700 font-medium"
            >
              <Shield className="h-4 w-4" />
              Usar app autenticadora
            </button>
          )}
          <span className="text-gray-300">|</span>
          <button
            type="button"
            onClick={() => {
              setMode("backup");
              setError(null);
              setBackupCode("");
            }}
            className="flex items-center gap-1.5 text-gray-500 hover:text-gray-700"
          >
            <KeyRound className="h-4 w-4" />
            Usar código de respaldo
          </button>
        </div>
      )}
    </div>
  );
}
