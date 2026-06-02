"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Shirt, Camera, Sparkles, MessageCircle } from "lucide-react";

export function OnboardingCard() {
  const router = useRouter();

  return (
    <div
      className="flex flex-1 flex-col items-center justify-center min-h-screen px-4 py-16 text-center"
      style={{ background: "linear-gradient(180deg,#F5F3FF 0%,#fff 55%)" }}
    >
      {/* Big indigo icon badge */}
      <div
        className="flex h-20 w-20 items-center justify-center rounded-2xl mb-6"
        style={{ background: "#6366F1", boxShadow: "0 10px 28px rgba(99,102,241,.35)" }}
      >
        <Shirt className="h-10 w-10 text-white" />
      </div>

      <h1
        className="text-3xl font-extrabold tracking-tight mb-2"
        style={{ color: "#111827" }}
      >
        ¡Bienvenida!
      </h1>
      <p className="text-base max-w-xs mb-8" style={{ color: "#6B7280" }}>
        Armemos tu primer catálogo. Empezá subiendo una prenda — el resto lo hace la IA.
      </p>

      {/* Feature points */}
      <div className="flex flex-col gap-4 w-full max-w-xs mb-8">
        {[
          {
            Icon: Camera,
            color: "#6366F1",
            bg: "#EEF0FF",
            title: "Subí una foto",
            desc: "Plana, en percha o maniquí",
          },
          {
            Icon: Sparkles,
            color: "#EC4899",
            bg: "#FCE7F3",
            title: "Elegí un modelo",
            desc: "La IA viste tu prenda",
          },
          {
            Icon: MessageCircle,
            color: "#10B981",
            bg: "#D1FAE5",
            title: "Compartí por WhatsApp",
            desc: "Link directo a tus clientas",
          },
        ].map(({ Icon, color, bg, title, desc }) => (
          <div key={title} className="flex items-center gap-3 text-left">
            <div
              className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl"
              style={{ background: bg, color }}
            >
              <Icon className="h-5 w-5" />
            </div>
            <div>
              <div className="text-sm font-bold" style={{ color: "#111827" }}>{title}</div>
              <div className="text-xs" style={{ color: "#6B7280" }}>{desc}</div>
            </div>
          </div>
        ))}
      </div>

      {/* CTAs */}
      <div className="flex flex-col gap-3 w-full max-w-xs">
        <Link
          href="/dashboard/prendas/nueva"
          className="flex h-12 w-full items-center justify-center rounded-full text-base font-semibold text-white transition-colors hover:bg-indigo-700"
          style={{ background: "#6366F1", boxShadow: "0 4px 14px rgba(99,102,241,.32)" }}
        >
          Subir mi primera prenda
        </Link>
        <button
          onClick={() => router.push("/dashboard")}
          className="flex h-11 w-full items-center justify-center rounded-full text-base font-semibold transition-colors hover:bg-indigo-50"
          style={{ color: "#6366F1", background: "transparent" }}
        >
          Explorar primero
        </button>
      </div>
    </div>
  );
}
