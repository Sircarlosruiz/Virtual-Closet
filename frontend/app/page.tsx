import Link from "next/link";
import { Button, buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import {
  Sparkles,
  Camera,
  Share2,
  Clock,
  Zap,
  Shirt,
  CheckCircle2,
  ArrowRight,
  MessageCircle,
  BarChart3,
  ShoppingBag,
  Layers,
  ChevronRight,
  ShieldCheck,
} from "lucide-react";

export default function HomePage() {
  return (
    <div className="flex flex-col w-full">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-foreground">
              <Shirt className="h-4 w-4 text-background" />
            </div>
            <span className="text-lg font-semibold tracking-tight">
              NikaCommerce
            </span>
          </div>
          <nav className="hidden items-center gap-6 text-sm font-medium md:flex">
            <Link
              href="#funcionalidades"
              className="text-muted-foreground transition-colors hover:text-foreground"
            >
              Funcionalidades
            </Link>
            <Link
              href="#como-funciona"
              className="text-muted-foreground transition-colors hover:text-foreground"
            >
              Cómo funciona
            </Link>
            <Link
              href="#testimonios"
              className="text-muted-foreground transition-colors hover:text-foreground"
            >
              Testimonios
            </Link>
          </nav>
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className={cn(buttonVariants({ variant: "ghost", size: "sm" }))}
            >
              Iniciar sesión
            </Link>
            <Link
              href="/register"
              className={cn(buttonVariants({ size: "sm" }))}
            >
              Crear cuenta
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden bg-slate-950 px-4 py-24 text-white sm:px-6 sm:py-32 lg:px-8">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-indigo-900/20 via-transparent to-transparent" />
        <div className="relative mx-auto max-w-7xl">
          <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-16">
            <div className="flex flex-col items-start gap-6">
              <Badge
                variant="secondary"
                className="bg-indigo-500/10 text-indigo-300 hover:bg-indigo-500/20"
              >
                <Sparkles className="mr-1 h-3 w-3" />
                Ahora con IDM-VTON integrado
              </Badge>
              <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl lg:text-6xl">
                Catálogos profesionales{" "}
                <span className="text-indigo-400">sin sesiones fotográficas</span>
              </h1>
              <p className="max-w-lg text-lg leading-8 text-slate-300">
                Transforma fotos planas o en maniquí de tus prendas en catálogos
                visuales sobre modelos reales usando Inteligencia Artificial, en
                menos de 5 minutos.
              </p>
              <div className="flex flex-col gap-3 sm:flex-row">
                <Link
                  href="/register"
                  className={cn(
                    buttonVariants({ size: "lg" }),
                    "bg-indigo-600 text-white hover:bg-indigo-500"
                  )}
                >
                  Empezar gratis
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
                <Link
                  href="#como-funciona"
                  className={cn(
                    buttonVariants({ variant: "outline", size: "lg" }),
                    "border-slate-700 bg-transparent text-white hover:bg-slate-800 hover:text-white"
                  )}
                >
                  Ver cómo funciona
                </Link>
              </div>
              <div className="flex items-center gap-4 text-sm text-slate-400">
                <div className="flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  <span>Sin tarjeta de crédito</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  <span>Prueba gratis de 14 días</span>
                </div>
              </div>
            </div>

            {/* Abstract Visual */}
            <div className="relative hidden lg:block">
              <div className="grid grid-cols-2 gap-4">
                <Card className="border-slate-800 bg-slate-900/60 backdrop-blur">
                  <CardContent className="flex flex-col items-center justify-center p-6 text-center">
                    <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-slate-800">
                      <Camera className="h-5 w-5 text-slate-300" />
                    </div>
                    <p className="text-sm font-medium text-slate-200">
                      Foto plana o maniquí
                    </p>
                    <p className="mt-1 text-xs text-slate-400">
                      Sube tu imagen original
                    </p>
                  </CardContent>
                </Card>
                <Card className="border-indigo-500/30 bg-indigo-950/40 backdrop-blur">
                  <CardContent className="flex flex-col items-center justify-center p-6 text-center">
                    <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-indigo-500/20">
                      <Sparkles className="h-5 w-5 text-indigo-300" />
                    </div>
                    <p className="text-sm font-medium text-indigo-100">
                      Procesamiento IA
                    </p>
                    <p className="mt-1 text-xs text-indigo-200/70">
                      IDM-VTON en segundos
                    </p>
                  </CardContent>
                </Card>
                <Card className="col-span-2 border-emerald-500/20 bg-emerald-950/30 backdrop-blur">
                  <CardContent className="flex flex-col items-center justify-center p-6 text-center">
                    <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/20">
                      <Share2 className="h-5 w-5 text-emerald-300" />
                    </div>
                    <p className="text-sm font-medium text-emerald-100">
                      Catálogo listo para compartir
                    </p>
                    <p className="mt-1 text-xs text-emerald-200/70">
                      Enlace directo por WhatsApp a tus revendedores
                    </p>
                  </CardContent>
                </Card>
              </div>
              {/* Decorative elements */}
              <div className="absolute -right-8 -top-8 h-32 w-32 rounded-full bg-indigo-500/10 blur-3xl" />
              <div className="absolute -bottom-8 -left-8 h-32 w-32 rounded-full bg-emerald-500/10 blur-3xl" />
            </div>
          </div>
        </div>
      </section>

      {/* Trust Bar */}
      <section className="border-b border-border bg-background px-4 py-10 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <p className="mb-6 text-center text-sm font-medium uppercase tracking-wider text-muted-foreground">
            Confiado por mayoristas de ropa en toda la región
          </p>
          <div className="flex flex-wrap items-center justify-center gap-8 opacity-60 grayscale transition-all hover:grayscale-0 sm:gap-12">
            {["ModaCentro", "Textiles del Sur", "RopaMayor", "EstiloB2B", "FashionHub"].map(
              (brand) => (
                <span
                  key={brand}
                  className="text-lg font-bold tracking-tight text-foreground"
                >
                  {brand}
                </span>
              )
            )}
          </div>
        </div>
      </section>

      {/* Problem / Solution */}
      <section id="como-funciona" className="bg-background px-4 py-24 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
              Olvídate de los altos costos de fotografía
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Las sesiones fotográficas tradicionales retrasan tus lanzamientos y
              consumen tu margen. Con Virtual Closet, subes tus fotos y la IA
              hace el resto.
            </p>
          </div>

          <div className="mt-16 grid gap-8 md:grid-cols-3">
            {[
              {
                icon: Camera,
                title: "Sube tus prendas",
                description:
                  "Fotos planas, en maniquí o colgadas. No necesitas equipo profesional ni modelos.",
                color: "bg-slate-100 text-slate-700",
              },
              {
                icon: Zap,
                title: "IA genera el catálogo",
                description:
                  "Nuestro motor IDM-VTON virtualiza tus prendas sobre modelos reales automáticamente.",
                color: "bg-indigo-100 text-indigo-700",
              },
              {
                icon: Share2,
                title: "Comparte y vende más",
                description:
                  "Envía catálogos digitales interactivos a tus revendedores vía WhatsApp en segundos.",
                color: "bg-emerald-100 text-emerald-700",
              },
            ].map((step, idx) => (
              <div key={step.title} className="relative flex flex-col items-center text-center">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl ${step.color}">
                  <step.icon className="h-6 w-6" />
                </div>
                <div className="mt-4 flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-slate-600">
                  0{idx + 1}
                </div>
                <h3 className="mt-4 text-lg font-semibold">{step.title}</h3>
                <p className="mt-2 text-muted-foreground">{step.description}</p>
                {idx < 2 && (
                  <ChevronRight className="absolute right-0 top-16 hidden h-6 w-6 text-border md:block" />
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="funcionalidades" className="bg-slate-50 px-4 py-24 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
              Todo lo que necesitas para escalar tus ventas
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Diseñado específicamente para mayoristas de ropa que quieren
              profesionalizar su presentación sin aumentar costos.
            </p>
          </div>

          <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {[
              {
                icon: Sparkles,
                title: "Virtualización IA",
                desc: "Tecnología IDM-VTON que viste modelos reales con tus prendas en minutos.",
              },
              {
                icon: Clock,
                title: "Menos de 5 min",
                desc: "Olvídate de jornadas de fotos. Genera cientos de looks en una mañana.",
              },
              {
                icon: Layers,
                title: "Catálogos digitales",
                desc: "Crea colecciones interactivas con precios, talles y stock en tiempo real.",
              },
              {
                icon: MessageCircle,
                title: "Comparte fácil",
                desc: "Enlaces directos para WhatsApp, email o redes sociales. Sin apps extra.",
              },
              {
                icon: ShoppingBag,
                title: "Gestión de stock",
                desc: "Sincroniza disponibilidad para que tus revendedores vean solo lo que hay.",
              },
              {
                icon: BarChart3,
                title: "Analytics simple",
                desc: "Sabe qué prendas generan más interés y optimiza tu inventario.",
              },
              {
                icon: ShieldCheck,
                title: "Seguridad B2B",
                desc: "Catálogos privados por cliente. Controla quién ve qué precios y productos.",
              },
              {
                icon: Zap,
                title: "Alto rendimiento",
                desc: "Plataforma optimizada para cargar rápido incluso con cientos de imágenes.",
              },
            ].map((feature) => (
              <Card
                key={feature.title}
                className="group border-border bg-white transition-all hover:border-indigo-200 hover:shadow-sm"
              >
                <CardContent className="flex flex-col items-start p-6">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100 transition-colors group-hover:bg-indigo-100">
                    <feature.icon className="h-5 w-5 text-slate-700 transition-colors group-hover:text-indigo-600" />
                  </div>
                  <h3 className="mt-4 font-semibold">{feature.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                    {feature.desc}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section id="testimonios" className="bg-background px-4 py-24 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
              Mayoristas que ya transformaron su negocio
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Cientos de empresas confían en Virtual Closet para presentar sus
              colecciones.
            </p>
          </div>

          <div className="mt-16 grid gap-8 md:grid-cols-3">
            {[
              {
                quote:
                  "Antes pagábamos miles por cada sesión fotográfica. Ahora generamos catálogos semanales en una tarde y nuestros revendedores reciben todo por WhatsApp.",
                author: "Mariana López",
                role: "Directora comercial, ModaCentro",
              },
              {
                quote:
                  "La virtualización con IA es sorprendente. La calidad visual es tan buena que nuestros clientes ni se dan cuenta de que no usamos modelos reales.",
                author: "Carlos Ríos",
                role: "CEO, Textiles del Sur",
              },
              {
                quote:
                  "Redujimos el tiempo de lanzamiento de nuevas colecciones de 3 semanas a 3 días. Eso se traduce en ventas más rápidas y menos stock estancado.",
                author: "Andrea Fernández",
                role: "Gerente de producto, FashionHub",
              },
            ].map((t) => (
              <Card key={t.author} className="border-border">
                <CardContent className="flex flex-col justify-between p-8">
                  <div>
                    <div className="flex gap-0.5">
                      {[...Array(5)].map((_, i) => (
                        <Sparkles
                          key={i}
                          className="h-4 w-4 fill-indigo-500 text-indigo-500"
                        />
                      ))}
                    </div>
                    <p className="mt-4 text-sm leading-relaxed text-foreground italic">
                      &ldquo;{t.quote}&rdquo;
                    </p>
                  </div>
                  <div className="mt-6">
                    <p className="text-sm font-semibold">{t.author}</p>
                    <p className="text-xs text-muted-foreground">{t.role}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="bg-slate-950 px-4 py-24 text-white sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl text-center">
          <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl lg:text-5xl">
            Empieza a vender más hoy mismo
          </h2>
          <p className="mx-auto mt-6 max-w-2xl text-lg leading-8 text-slate-300">
            Únete a los mayoristas que ya eliminaron los costos de fotografía y
            aceleraron sus ventas con catálogos profesionales generados por IA.
          </p>
          <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link
              href="/register"
              className={cn(
                buttonVariants({ size: "lg" }),
                "bg-indigo-600 text-white hover:bg-indigo-500"
              )}
            >
              Crear cuenta gratis
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
            <Button
              size="lg"
              variant="outline"
              className="border-slate-700 bg-transparent text-white hover:bg-slate-800 hover:text-white"
            >
              Hablar con ventas
            </Button>
          </div>
          <p className="mt-6 text-sm text-slate-400">
            Prueba gratuita de 14 días. Sin compromisos, sin tarjeta.
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border bg-background px-4 py-12 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-foreground">
                  <Shirt className="h-4 w-4 text-background" />
                </div>
                <span className="text-lg font-semibold">NikaCommerce</span>
              </div>
              <p className="mt-4 text-sm text-muted-foreground">
                La plataforma B2B para mayoristas de ropa que quieren catálogos
                profesionales sin costos fotográficos.
              </p>
            </div>
            <div>
              <h4 className="text-sm font-semibold">Producto</h4>
              <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
                <li>
                  <Link href="#funcionalidades" className="hover:text-foreground">
                    Funcionalidades
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-foreground">
                    Precios
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-foreground">
                    Integraciones
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="text-sm font-semibold">Empresa</h4>
              <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
                <li>
                  <Link href="#" className="hover:text-foreground">
                    Sobre nosotros
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-foreground">
                    Blog
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-foreground">
                    Contacto
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="text-sm font-semibold">Legal</h4>
              <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
                <li>
                  <Link href="#" className="hover:text-foreground">
                    Privacidad
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-foreground">
                    Términos de uso
                  </Link>
                </li>
              </ul>
            </div>
          </div>
          <div className="mt-12 border-t border-border pt-8 text-center text-sm text-muted-foreground">
            © {new Date().getFullYear()} NikaCommerce. Todos los derechos
            reservados.
          </div>
        </div>
      </footer>
    </div>
  );
}
