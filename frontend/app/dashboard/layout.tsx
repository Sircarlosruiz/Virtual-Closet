import { ClientRedirect } from "@/components/dashboard/ClientRedirect";
import { Toaster } from "@/components/ui/sonner";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

async function getMe(): Promise<{ prendas_count: number } | null> {
  try {
    const { cookies } = await import("next/headers");
    const cookieStore = await cookies();
    const token = cookieStore.get("access_token")?.value;

    if (!token) return null;

    const res = await fetch(`${BACKEND_URL}/api/auth/me`, {
      headers: {
        Cookie: `access_token=${token}`,
      },
      cache: "no-store",
    });

    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const me = await getMe();

  if (!me) {
    return <ClientRedirect href="/login" />;
  }

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
      {children}
      <Toaster />
    </div>
  );
}
