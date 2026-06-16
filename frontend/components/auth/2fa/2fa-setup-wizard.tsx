"use client";

import { useState, useCallback } from "react";
import { MethodSelector } from "./method-selector";
import { TotpSetupStep } from "./totp-setup-step";
import { SmsSetupStep } from "./sms-setup-step";
import { BackupCodesStep } from "./backup-codes-step";
import { apiFetchWithChallenge } from "@/lib/auth/challenge-context";

type WizardStep = "select" | "totp-setup" | "sms-setup" | "backup-codes" | "done";

interface TwoFactorSetupWizardProps {
  onComplete: () => void;
}

export function TwoFactorSetupWizard({ onComplete }: TwoFactorSetupWizardProps) {
  const [step, setStep] = useState<WizardStep>("select");
  const [method, setMethod] = useState<"totp" | "sms">("totp");
  const [totpData, setTotpData] = useState<{
    otpauthUri: string;
    secret: string;
    backupCodes: string[];
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleMethodSelect = useCallback(async (selected: "totp" | "sms") => {
    setMethod(selected);
    setLoading(true);
    setError(null);

    try {
      const result = await apiFetchWithChallenge("/api/auth/2fa/setup", {
        method: "POST",
        body: JSON.stringify({
          method: selected,
          phone_number: undefined,
        }),
      }) as { totp_secret?: string; otpauth_uri?: string; backup_codes?: string[]; phone_number?: string; otp_sent?: boolean };

      if (selected === "totp" && result.totp_secret && result.otpauth_uri && result.backup_codes) {
        setTotpData({
          otpauthUri: result.otpauth_uri,
          secret: result.totp_secret,
          backupCodes: result.backup_codes,
        });
        setStep("totp-setup");
      } else if (selected === "sms") {
        setStep("sms-setup");
      }
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("No se pudo iniciar la configuración. Intentá de nuevo.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const handleTotpConfirm = useCallback(async (otpCode: string) => {
    await apiFetchWithChallenge("/api/auth/2fa/setup/confirm", {
      method: "POST",
      body: JSON.stringify({ otp_code: otpCode }),
    });
    if (totpData) {
      setStep("backup-codes");
    }
  }, [totpData]);

  const handleSmsSend = useCallback(async (phoneNumber: string) => {
    await apiFetchWithChallenge("/api/auth/2fa/setup", {
      method: "POST",
      body: JSON.stringify({ method: "sms", phone_number: phoneNumber }),
    });
  }, []);

  const handleSmsConfirm = useCallback(async (otpCode: string) => {
    await apiFetchWithChallenge("/api/auth/2fa/setup/confirm", {
      method: "POST",
      body: JSON.stringify({ otp_code: otpCode }),
    });
    setStep("backup-codes");
  }, []);

  const handleContinue = useCallback(() => {
    setStep("done");
    onComplete();
  }, [onComplete]);

  if (loading) {
    return (
      <div className="flex flex-col items-center gap-4 py-12">
        <div className="h-8 w-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
        <p className="text-sm text-gray-500">Cargando configuración...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center gap-4 py-8">
        <p className="text-sm text-red-500 text-center">{error}</p>
        <button
          type="button"
          onClick={() => {
            setError(null);
            setStep("select");
          }}
          className="text-sm font-medium text-indigo-600 hover:text-indigo-700"
        >
          Intentar de nuevo
        </button>
      </div>
    );
  }

  switch (step) {
    case "select":
      return <MethodSelector onSelect={handleMethodSelect} />;

    case "totp-setup":
      return totpData ? (
        <TotpSetupStep
          otpauthUri={totpData.otpauthUri}
          secret={totpData.secret}
          onConfirm={handleTotpConfirm}
          onBack={() => setStep("select")}
        />
      ) : null;

    case "sms-setup":
      return (
        <SmsSetupStep
          onSendOtp={handleSmsSend}
          onConfirm={handleSmsConfirm}
          onBack={() => setStep("select")}
        />
      );

    case "backup-codes":
      return totpData ? (
        <BackupCodesStep codes={totpData.backupCodes} onContinue={handleContinue} />
      ) : null;

    default:
      return null;
  }
}
