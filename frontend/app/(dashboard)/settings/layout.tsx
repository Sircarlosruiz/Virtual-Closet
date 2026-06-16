import Link from "next/link";

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const navItems = [
    { href: "/settings/account", label: "Cuenta y admins" },
    { href: "/settings/buyer-links", label: "Enlaces de comprador" },
  ];

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <h1 className="text-2xl font-bold text-zinc-900 mb-6">Configuración</h1>

      {/* Settings navigation */}
      <nav className="flex gap-1 mb-8 border-b">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="px-4 py-2 text-sm font-medium text-zinc-500 hover:text-zinc-900 border-b-2 border-transparent hover:border-zinc-300 transition-colors data-[active=true]:text-indigo-600 data-[active=true]:border-indigo-600"
          >
            {item.label}
          </Link>
        ))}
      </nav>

      {children}
    </div>
  );
}
