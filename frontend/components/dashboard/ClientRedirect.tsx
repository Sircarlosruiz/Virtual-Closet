"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/** Client-side redirect — avoids Turbopack dev bug with server redirect() + performance.measure */
export function ClientRedirect({ href }: { href: string }) {
  const router = useRouter();

  useEffect(() => {
    router.replace(href);
  }, [href, router]);

  return (
    <div className="flex min-h-[40vh] items-center justify-center text-sm text-zinc-500">
      Redirigiendo…
    </div>
  );
}
