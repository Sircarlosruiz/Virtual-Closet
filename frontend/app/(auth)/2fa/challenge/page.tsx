"use client";

import { useRouter } from "next/navigation";
import { useChallenge } from "@/lib/auth/challenge-context";
import { TwoFactorChallenge } from "@/components/auth/2fa/two-factor-challenge";

export default function TwoFaChallengePage() {
  const router = useRouter();
  const { clearChallenge } = useChallenge();

  const handleSuccess = () => {
    clearChallenge();
    router.push("/dashboard");
    router.refresh();
  };

  return (
    <div className="flex flex-col gap-4">
      <TwoFactorChallenge onSuccess={handleSuccess} />
    </div>
  );
}
