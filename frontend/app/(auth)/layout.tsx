import { Toaster } from "@/components/ui/sonner";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 px-4 dark:bg-zinc-950">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
            Virtual Closet
          </h1>
          <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
            NikaCommerce
          </p>
        </div>
        {children}
      </div>
      <Toaster />
    </div>
  );
}
