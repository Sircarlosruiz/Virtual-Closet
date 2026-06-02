import Link from "next/link";
import {
  Sparkles,
  Camera,
  CheckCircle2,
  ArrowRight,
  Shirt,
  MessageCircle,
} from "lucide-react";

const StarIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4 text-yellow-400">
    <path d="m12 2 2.9 6.3 6.9.7-5.1 4.6 1.4 6.8L12 17.8 6 20.4l1.4-6.8L2.3 9l6.9-.7z" />
  </svg>
);

export default function HomePage() {
  return (
    <div className="flex flex-col w-full min-h-screen" style={{ fontFamily: "Inter, -apple-system, system-ui, sans-serif" }}>
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b" style={{ background: "rgba(255,255,255,0.92)", backdropFilter: "blur(12px)", borderColor: "#E5E7EB" }}>
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          {/* Logo */}
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg" style={{ background: "#111827" }}>
              <Shirt className="h-4 w-4 text-white" />
            </div>
            <span className="text-base font-bold tracking-tight" style={{ color: "#111827" }}>
              Virtual Closet
            </span>
          </div>

          {/* Nav — desktop only */}
          <nav className="hidden items-center gap-6 text-sm font-medium md:flex">
            <a href="#como-funciona" className="transition-colors hover:text-indigo-600" style={{ color: "#6B7280" }}>
              Cómo funciona
            </a>
            <a href="#funcionalidades" className="transition-colors hover:text-indigo-600" style={{ color: "#6B7280" }}>
              Funcionalidades
            </a>
            <a href="#precios" className="transition-colors hover:text-indigo-600" style={{ color: "#6B7280" }}>
              Precios
            </a>
          </nav>

          {/* Auth buttons */}
          <div className="flex items-center gap-2">
            <Link
              href="/login"
              className="hidden sm:inline-flex items-center px-4 py-2 text-sm font-semibold rounded-full transition-colors hover:bg-gray-100"
              style={{ color: "#111827" }}
            >
              Iniciar sesión
            </Link>
            <Link
              href="/registro"
              className="inline-flex items-center px-4 py-2 text-sm font-semibold rounded-full text-white bg-indigo-500 transition-colors hover:bg-indigo-600"
            >
              Crear cuenta
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden text-white" style={{ background: "#0B1020" }}>
        {/* Radial glow decorations */}
        <div
          className="pointer-events-none absolute -top-32 right-0 h-[500px] w-[500px] rounded-full opacity-20"
          style={{ background: "radial-gradient(circle, #6366F1, transparent 70%)" }}
        />
        <div
          className="pointer-events-none absolute bottom-0 left-0 h-[300px] w-[300px] rounded-full opacity-10"
          style={{ background: "radial-gradient(circle, #EC4899, transparent 70%)" }}
        />

        <div className="relative mx-auto max-w-6xl px-4 sm:px-6" style={{ padding: "88px 24px" }}>
          <div className="grid items-center gap-14 lg:grid-cols-2">
            {/* Left: copy */}
            <div className="flex flex-col items-start gap-5">
              {/* Badge */}
              <span
                className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold"
                style={{ background: "rgba(99,102,241,.18)", color: "#C7D2FE", border: "1px solid rgba(99,102,241,.3)" }}
              >
                <Sparkles className="h-3 w-3" />
                Catálogos con IA para mayoristas
              </span>

              <h1 className="text-4xl font-extrabold tracking-tight leading-tight sm:text-5xl">
                Catálogos profesionales{" "}
                <span style={{ color: "#EC4899" }}>sin sesiones de fotos</span>
              </h1>

              <p className="max-w-lg text-base leading-relaxed" style={{ color: "#94A3B8" }}>
                Subí una foto plana o en maniquí de tu prenda y la IA la viste sobre un modelo real.
                Tu catálogo listo para WhatsApp en menos de 5 minutos.
              </p>

              <div className="flex flex-col gap-3 sm:flex-row">
                <Link
                  href="/registro"
                  className="inline-flex items-center justify-center gap-2 rounded-full px-6 py-3 text-base font-semibold text-white transition-colors"
                  style={{ background: "#6366F1", boxShadow: "0 4px 14px rgba(99,102,241,.4)" }}
                >
                  Empezar gratis
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <a
                  href="#como-funciona"
                  className="inline-flex items-center justify-center rounded-full px-6 py-3 text-base font-semibold transition-colors"
                  style={{ border: "1.5px solid rgba(255,255,255,.2)", color: "#fff", background: "transparent" }}
                >
                  Ver cómo funciona
                </a>
              </div>

              <div className="flex items-center gap-5 text-sm" style={{ color: "#94A3B8" }}>
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4" style={{ color: "#34D399" }} />
                  Sin tarjeta de crédito
                </span>
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4" style={{ color: "#34D399" }} />
                  30 días de prueba
                </span>
              </div>
            </div>

            {/* Right: hero cards */}
            <div className="hidden lg:grid grid-cols-2 gap-4">
              {/* Card 1: Camera */}
              <div
                className="rounded-2xl p-5"
                style={{ background: "rgba(148,163,184,.1)", border: "1px solid rgba(148,163,184,.15)" }}
              >
                <div
                  className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl"
                  style={{ background: "rgba(148,163,184,.2)", color: "#CBD5E1" }}
                >
                  <Camera className="h-5 w-5" />
                </div>
                <div className="text-sm font-semibold text-white">Foto plana o maniquí</div>
                <div className="mt-1 text-xs" style={{ color: "#94A3B8" }}>Subí tu imagen original</div>
              </div>

              {/* Card 2: Sparkles */}
              <div
                className="rounded-2xl p-5"
                style={{ background: "rgba(99,102,241,.14)", border: "1px solid rgba(99,102,241,.3)" }}
              >
                <div
                  className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl"
                  style={{ background: "rgba(99,102,241,.25)", color: "#C7D2FE" }}
                >
                  <Sparkles className="h-5 w-5" />
                </div>
                <div className="text-sm font-semibold" style={{ color: "#E0E7FF" }}>La IA viste el modelo</div>
                <div className="mt-1 text-xs" style={{ color: "#C7D2FE" }}>En segundos, look real</div>
              </div>

              {/* Card 3: WhatsApp — full width */}
              <div
                className="col-span-2 rounded-2xl p-5"
                style={{ background: "rgba(236,72,153,.12)", border: "1px solid rgba(236,72,153,.28)" }}
              >
                <div
                  className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl"
                  style={{ background: "rgba(236,72,153,.22)", color: "#FBCFE8" }}
                >
                  <MessageCircle className="h-5 w-5" />
                </div>
                <div className="text-sm font-semibold" style={{ color: "#FCE7F3" }}>Catálogo listo para compartir</div>
                <div className="mt-1 text-xs" style={{ color: "#FBCFE8" }}>
                  Link directo por WhatsApp a tus revendedoras
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Cómo funciona */}
      <section id="como-funciona" className="py-20 px-4 sm:px-6" style={{ background: "#FFFFFF" }}>
        <div className="mx-auto max-w-6xl">
          <div className="text-center mb-12">
            <div
              className="mb-3 inline-block text-xs font-bold uppercase tracking-widest"
              style={{ color: "#6366F1" }}
            >
              Cómo funciona
            </div>
            <h2 className="text-3xl font-extrabold tracking-tight" style={{ color: "#111827" }}>
              Tu catálogo en tres pasos
            </h2>
            <p className="mt-4 max-w-xl mx-auto text-base" style={{ color: "#6B7280" }}>
              Sin fotógrafo, sin estudio, sin esperar semanas. Vos subís, la IA trabaja, vos compartís.
            </p>
          </div>

          <div className="grid gap-8 md:grid-cols-3">
            {[
              {
                Icon: Camera,
                bg: "#EEF0FF",
                color: "#6366F1",
                num: "01",
                title: "Subí tu prenda",
                desc: "Foto plana, en percha o maniquí. No necesitás equipo profesional ni modelos.",
              },
              {
                Icon: Sparkles,
                bg: "#EEF0FF",
                color: "#6366F1",
                num: "02",
                title: "La IA la viste",
                desc: "Vestimos tu prenda sobre un modelo real con luz natural, automáticamente.",
              },
              {
                Icon: MessageCircle,
                bg: "#FCE7F3",
                color: "#EC4899",
                num: "03",
                title: "Compartí y vendé",
                desc: "Armás un catálogo con link único y lo mandás por WhatsApp a tus revendedoras.",
              },
            ].map((step) => (
              <div key={step.num} className="flex flex-col items-center text-center px-4">
                <div
                  className="flex h-14 w-14 items-center justify-center rounded-2xl mb-4"
                  style={{ background: step.bg, color: step.color }}
                >
                  <step.Icon className="h-6 w-6" />
                </div>
                <div
                  className="text-xs font-bold mb-2"
                  style={{ color: "#6366F1" }}
                >
                  {step.num}
                </div>
                <h3 className="text-lg font-bold mb-2" style={{ color: "#111827" }}>{step.title}</h3>
                <p className="text-sm leading-relaxed" style={{ color: "#6B7280" }}>{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Social proof */}
      <section id="funcionalidades" className="py-20 px-4 sm:px-6" style={{ background: "#F9FAFB" }}>
        <div className="mx-auto max-w-6xl">
          <div className="text-center mb-10">
            <div
              className="mb-3 inline-block text-xs font-bold uppercase tracking-widest"
              style={{ color: "#6366F1" }}
            >
              Confían en nosotras
            </div>
            <h2 className="text-3xl font-extrabold tracking-tight" style={{ color: "#111827" }}>
              Mayoristas que ya transformaron su negocio
            </h2>
          </div>

          {/* Brand logos row */}
          <div className="flex flex-wrap items-center justify-center gap-6 mb-12">
            {["ModaCentro", "Textiles del Sur", "RopaMayor", "EstiloB2B", "FashionHub"].map((b) => (
              <span
                key={b}
                className="text-base font-bold"
                style={{ color: "#9CA3AF" }}
              >
                {b}
              </span>
            ))}
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-6 mb-12 max-w-2xl mx-auto text-center">
            {[
              { big: "5 min", label: "para tu primer catálogo" },
              { big: "$0", label: "en fotógrafo o estudio" },
              { big: "+3x", label: "más rápido al lanzar" },
            ].map((s) => (
              <div key={s.label}>
                <div className="text-4xl font-extrabold tracking-tight" style={{ color: "#6366F1" }}>
                  {s.big}
                </div>
                <div className="mt-1 text-sm" style={{ color: "#6B7280" }}>{s.label}</div>
              </div>
            ))}
          </div>

          {/* Testimonials */}
          <div className="grid gap-6 md:grid-cols-3">
            {[
              {
                q: "Antes pagábamos miles por cada sesión. Ahora armo el catálogo en una tarde y mis revendedoras reciben todo por WhatsApp.",
                a: "Mariana López",
                r: "ModaCentro, Managua",
              },
              {
                q: "La calidad es tan buena que mis clientas ni se dan cuenta de que no usé modelos reales.",
                a: "Carla Ríos",
                r: "Boutique Karla, León",
              },
              {
                q: "Pasé de 3 semanas a 3 días para lanzar una colección nueva. Vendo más y me queda menos stock.",
                a: "Andrea Fernández",
                r: "EstiloB2B, Estelí",
              },
            ].map((t) => (
              <div
                key={t.a}
                className="rounded-2xl p-6"
                style={{ background: "#FFFFFF", border: "1px solid #E5E7EB", boxShadow: "0 1px 3px rgba(17,24,39,.05)" }}
              >
                <div className="flex gap-0.5 mb-3">
                  {[0, 1, 2, 3, 4].map((i) => <StarIcon key={i} />)}
                </div>
                <p className="text-sm leading-relaxed mb-4 italic" style={{ color: "#374151" }}>
                  &ldquo;{t.q}&rdquo;
                </p>
                <div>
                  <div className="text-sm font-bold" style={{ color: "#111827" }}>{t.a}</div>
                  <div className="text-xs" style={{ color: "#6B7280" }}>{t.r}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section id="precios" className="py-24 px-4 sm:px-6 text-center" style={{ background: "#0B1020", color: "#fff" }}>
        <div className="mx-auto max-w-2xl">
          <h2 className="text-3xl font-extrabold tracking-tight sm:text-4xl mb-4">
            Empezá a vender más hoy mismo
          </h2>
          <p className="text-base mb-8" style={{ color: "#94A3B8" }}>
            Unite a las mayoristas que ya eliminaron los costos de fotografía y aceleraron sus ventas
            con catálogos generados por IA.
          </p>
          <Link
            href="/registro"
            className="inline-flex items-center gap-2 rounded-full px-8 py-4 text-base font-bold text-white"
            style={{ background: "#6366F1", boxShadow: "0 4px 14px rgba(99,102,241,.4)" }}
          >
            Crear cuenta gratis
            <ArrowRight className="h-4 w-4" />
          </Link>
          <p className="mt-5 text-sm" style={{ color: "#64748B" }}>
            Prueba de 30 días · sin compromiso · sin tarjeta.
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-6 px-4 sm:px-6" style={{ background: "#0B1020", borderColor: "rgba(255,255,255,.08)" }}>
        <div className="mx-auto max-w-6xl flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2" style={{ color: "#fff" }}>
            <div className="flex h-6 w-6 items-center justify-center rounded-md" style={{ background: "#111827" }}>
              <Shirt className="h-3 w-3 text-white" />
            </div>
            <span className="text-sm font-bold">Virtual Closet</span>
          </div>
          <div className="text-sm" style={{ color: "#64748B" }}>
            © 2026 NikaCommerce · Hecho en Nicaragua 🇳🇮
          </div>
        </div>
      </footer>
    </div>
  );
}
