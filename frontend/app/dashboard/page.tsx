import { redirect } from "next/navigation";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

async function getPrendasCount(): Promise<number | null> {
  try {
    const { cookies } = await import("next/headers");
    const cookieStore = await cookies();
    const token = cookieStore.get("access_token")?.value;
    if (!token) return null;

    const res = await fetch(`${BACKEND_URL}/api/auth/me`, {
      headers: { Cookie: `access_token=${token}` },
      cache: "no-store",
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data.prendas_count ?? 0;
  } catch {
    return null;
  }
}

export default async function DashboardPage() {
  const prendasCount = await getPrendasCount();
  if (prendasCount === 0) {
    redirect("/dashboard/onboarding");
  }

  return (
    <div className="flex flex-1 items-center justify-center">
      <div className="text-center">
        <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
          Dashboard
        </h1>
        <p className="mt-2 text-zinc-600 dark:text-zinc-400">
          Bienvenido a tu panel de Virtual Closet
        </p>
      </div>
    </div>
  );
}
