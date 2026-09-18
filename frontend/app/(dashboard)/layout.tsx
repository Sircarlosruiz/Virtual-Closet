import { ClientRedirect } from "@/components/dashboard/ClientRedirect";
import { DashboardShell } from "@/components/dashboard/DashboardShell";
import { Toaster } from "@/components/ui/sonner";
import { getServerMe } from "@/lib/auth/get-server-me";

export default async function DashboardGroupLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const me = await getServerMe();

  if (!me) {
    return <ClientRedirect href="/login" />;
  }

  return (
    <DashboardShell
      user={{
        nombre_negocio: me.nombre_negocio,
        email: me.email,
        plan: me.plan,
        trial_activo: me.trial_activo,
        role: me.role,
      }}
    >
      {children}
      <Toaster />
    </DashboardShell>
  );
}
