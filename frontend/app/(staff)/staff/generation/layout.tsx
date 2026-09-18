import { ClientRedirect } from '@/components/dashboard/ClientRedirect';
import { DashboardShell } from '@/components/dashboard/DashboardShell';
import { StaffUnauthorized } from '@/components/staff-generation/StaffUnauthorized';
import { Toaster } from '@/components/ui/sonner';
import { isStaffRole } from '@/lib/api/auth';
import { getServerMe } from '@/lib/auth/get-server-me';

export default async function StaffGenerationLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const me = await getServerMe();

  if (!me) {
    return <ClientRedirect href="/login" />;
  }

  const user = {
    nombre_negocio: me.nombre_negocio,
    email: me.email,
    plan: me.plan,
    trial_activo: me.trial_activo,
    role: me.role,
  };

  if (!isStaffRole(me.role)) {
    return (
      <DashboardShell user={user}>
        <StaffUnauthorized />
        <Toaster />
      </DashboardShell>
    );
  }

  return (
    <DashboardShell user={user}>
      {children}
      <Toaster />
    </DashboardShell>
  );
}
