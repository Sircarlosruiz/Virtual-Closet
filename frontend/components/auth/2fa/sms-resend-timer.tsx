"use client";

import { useState, useEffect, useCallback } from "react";

interface SmsResendTimerProps {
  onResend: () => Promise<void>;
  initialCooldown?: number;
}

export function SmsResendTimer({ onResend, initialCooldown = 30 }: SmsResendTimerProps) {
  const [seconds, setSeconds] = useState(0);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canResend = seconds <= 0;

  const startCooldown = useCallback((duration: number) => {
    setSeconds(duration);
  }, []);

  useEffect(() => {
    if (seconds <= 0) return;

    const timer = setInterval(() => {
      setSeconds((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [seconds > 0]);

  const handleResend = async () => {
    if (!canResend || sending) return;
    setError(null);
    setSending(true);
    try {
      await onResend();
      startCooldown(initialCooldown);
    } catch (err) {
      if (err instanceof Error) {
        // Check for rate limit with retry_after
        const rateLimitMatch = err.message.match(/(\d+)\s*seconds?/);
        if (rateLimitMatch) {
          const retryAfter = parseInt(rateLimitMatch[1], 10);
          startCooldown(retryAfter);
          setError(`Esperá ${retryAfter} segundos antes de reenviar.`);
        } else {
          setError(err.message);
        }
      } else {
        setError("No se pudo reenviar el código. Intentá de nuevo.");
      }
    } finally {
      setSending(false);
    }
  };

  if (canResend && !error) {
    return (
      <button
        type="button"
        onClick={handleResend}
        disabled={sending}
        className="text-sm font-medium text-indigo-600 hover:text-indigo-700 transition-colors disabled:opacity-50"
      >
        {sending ? "Enviando..." : "Reenviar código"}
      </button>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center gap-2">
        <p className="text-sm text-red-500">{error}</p>
        {seconds > 0 && (
          <p className="text-xs text-gray-400">
            Podés reenviar en {seconds}s
          </p>
        )}
      </div>
    );
  }

  return (
    <p className="text-sm text-gray-400">
      Podés reenviar en {seconds}s
    </p>
  );
}
