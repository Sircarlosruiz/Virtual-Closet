import { Toaster } from "@/components/ui/sonner";

export default function PortalLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-100 to-zinc-50 dark:from-zinc-950 dark:to-zinc-900">
      <header className="border-b bg-white/80 dark:bg-zinc-900/80 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">
            Catálogo
          </h1>
        </div>
      </header>
      <main>{children}</main>
      <Toaster />
    </div>
  );
}
