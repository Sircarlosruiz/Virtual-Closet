"use client";

import { createContext, useContext, useState, useCallback, useEffect } from "react";

const CHALLENGE_TOKEN_KEY = "vc_challenge_token";
const CHALLENGE_EMAIL_KEY = "vc_challenge_email";
const CHALLENGE_SETUP_KEY = "vc_requires_setup";

interface ChallengeState {
  token: string | null;
  userEmail: string | null;
  requiresSetup: boolean;
  setChallenge: (token: string, email?: string, requiresSetup?: boolean) => void;
  clearChallenge: () => void;
}

const ChallengeContext = createContext<ChallengeState>({
  token: null,
  userEmail: null,
  requiresSetup: false,
  setChallenge: () => {},
  clearChallenge: () => {},
});

export function ChallengeProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [requiresSetup, setRequiresSetup] = useState(false);

  useEffect(() => {
    const storedToken = sessionStorage.getItem(CHALLENGE_TOKEN_KEY);
    const storedEmail = sessionStorage.getItem(CHALLENGE_EMAIL_KEY);
    const storedSetup = sessionStorage.getItem(CHALLENGE_SETUP_KEY);
    if (storedToken) setToken(storedToken);
    if (storedEmail) setUserEmail(storedEmail);
    if (storedSetup === "true") setRequiresSetup(true);
  }, []);

  const setChallenge = useCallback(
    (newToken: string, email?: string, requiresSetupFlag?: boolean) => {
      setToken(newToken);
      sessionStorage.setItem(CHALLENGE_TOKEN_KEY, newToken);
      if (email) {
        setUserEmail(email);
        sessionStorage.setItem(CHALLENGE_EMAIL_KEY, email);
      }
      if (requiresSetupFlag !== undefined) {
        setRequiresSetup(requiresSetupFlag);
        sessionStorage.setItem(CHALLENGE_SETUP_KEY, String(requiresSetupFlag));
      }
    },
    []
  );

  const clearChallenge = useCallback(() => {
    setToken(null);
    setUserEmail(null);
    setRequiresSetup(false);
    sessionStorage.removeItem(CHALLENGE_TOKEN_KEY);
    sessionStorage.removeItem(CHALLENGE_EMAIL_KEY);
    sessionStorage.removeItem(CHALLENGE_SETUP_KEY);
  }, []);

  return (
    <ChallengeContext.Provider
      value={{ token, userEmail, requiresSetup, setChallenge, clearChallenge }}
    >
      {children}
    </ChallengeContext.Provider>
  );
}

export function useChallenge() {
  const context = useContext(ChallengeContext);
  if (!context) {
    throw new Error("useChallenge must be used within ChallengeProvider");
  }
  return context;
}

export async function apiFetchWithChallenge(
  path: string,
  options: RequestInit = {}
): Promise<unknown> {
  const token = sessionStorage.getItem(CHALLENGE_TOKEN_KEY);
  if (!token) {
    throw new Error("No challenge token available");
  }

  const { BACKEND_URL } = await import("@/lib/api");
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;

  const response = await fetch(`${BACKEND_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: isFormData
      ? { ...options.headers, Authorization: `Bearer ${token}` }
      : {
          "Content-Type": "application/json",
          ...options.headers,
          Authorization: `Bearer ${token}`,
        },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Error desconocido" }));
    const detail = error.detail;
    let message: string;
    let code: string | undefined;

    if (typeof detail === "string") {
      message = detail;
    } else if (typeof detail === "object" && detail !== null) {
      code = detail.code;
      message = detail.message || "Error del servidor";
    } else if (Array.isArray(detail)) {
      message = detail.map((e: { msg?: string }) => e.msg ?? "Dato inválido").join(". ");
    } else {
      message = `HTTP ${response.status}`;
    }

    const err = new Error(message) as Error & { code?: string; status?: number };
    err.code = code;
    err.status = response.status;
    throw err;
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}
