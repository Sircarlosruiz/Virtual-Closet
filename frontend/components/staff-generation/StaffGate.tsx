'use client';

import { isStaffRole } from '@/lib/api/auth';

interface StaffGateProps {
  role: string | undefined;
  children: React.ReactNode;
}

export function StaffGate({ role, children }: StaffGateProps) {
  if (!isStaffRole(role)) {
    return null;
  }
  return <>{children}</>;
}
