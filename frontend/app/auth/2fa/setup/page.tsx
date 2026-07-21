"use client";

import { useRouter } from "next/navigation";
import { useChallenge } from "@/lib/auth/challenge-context";
import { TwoFactorSetupWizard } from "@/components/auth/2fa/2fa-setup-wizard";

export default function TwoFaSetupPage() {
  const router = useRouter();
  const { clearChallenge } = useChallenge();

  const handleComplete = () => {
    clearChallenge();
    router.push("/dashboard");
    router.refresh();
  };

  return (
    <div className="flex flex-col gap-4">
      <TwoFactorSetupWizard onComplete={handleComplete} />
    </div>
  );
}
