import { Toaster } from "@/components/ui/sonner";
import { Shirt, CheckCircle2 } from "lucide-react";

export function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen">
      {/* Brand pane — hidden on mobile */}
      <div
        className="hidden lg:flex flex-1 flex-col p-14 relative overflow-hidden"
        style={{ background: "#0B1020", color: "#fff" }}
      >
        {/* Radial glow decorations */}
        <div
          className="pointer-events-none absolute -top-24 -right-24 h-96 w-96 rounded-full opacity-25"
          style={{ background: "radial-gradient(circle, #6366F1, transparent 70%)" }}
        />
        <div
          className="pointer-events-none absolute bottom-0 left-0 h-64 w-64 rounded-full opacity-15"
          style={{ background: "radial-gradient(circle, #EC4899, transparent 70%)" }}
        />

        {/* Brand logo + name */}
        <div className="flex items-center gap-2.5 relative z-10">
          <div
            className="flex h-8 w-8 items-center justify-center rounded-lg"
            style={{ background: "#1E293B" }}
          >
            <Shirt className="h-4 w-4 text-white" />
          </div>
          <span className="text-lg font-bold tracking-tight">Virtual Closet</span>
        </div>

        {/* Quote + feature bullets */}
        <div className="flex flex-1 flex-col justify-center relative z-10">
          <blockquote
            className="text-xl font-semibold leading-relaxed mb-8"
            style={{ color: "#E2E8F0" }}
          >
            &ldquo;Subí una foto de tu prenda y en menos de 5 minutos tenés un catálogo
            profesional para mandar por WhatsApp.&rdquo;
          </blockquote>

          <div className="flex flex-col gap-3">
            {[
              "30 días de prueba, sin tarjeta",
              "Modelos con IA, luz natural y look real",
              "Compartí por WhatsApp con un link",
            ].map((item) => (
              <div key={item} className="flex items-center gap-3">
                <CheckCircle2
                  className="h-5 w-5 flex-shrink-0"
                  style={{ color: "#6366F1" }}
                />
                <span className="text-sm font-medium" style={{ color: "#CBD5E1" }}>
                  {item}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Form pane */}
      <div className="w-full lg:w-[480px] flex items-center justify-center p-10 bg-white">
        <div className="w-full max-w-[360px]">{children}</div>
      </div>

      <Toaster />
    </div>
  );
}

export default AuthLayout;
