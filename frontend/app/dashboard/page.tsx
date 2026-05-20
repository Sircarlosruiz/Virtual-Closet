import { redirect } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";

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
    <div className="flex flex-1 flex-col p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
          Mis prendas
        </h1>
        <Link href="/dashboard/prendas/nueva">
          <Button>Nueva prenda</Button>
        </Link>
      </div>
      <p className="text-zinc-600 dark:text-zinc-400">
        Tienes {prendasCount} prenda{prendasCount !== 1 ? "s" : ""} en tu closet
      </p>
    </div>
  );
}
