import type { MayoristaProfile } from '@/lib/api/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function getServerMe(): Promise<MayoristaProfile | null> {
  try {
    const { cookies } = await import('next/headers');
    const cookieStore = await cookies();
    const token = cookieStore.get('access_token')?.value;

    if (!token) return null;

    const res = await fetch(`${BACKEND_URL}/api/auth/me`, {
      headers: {
        Cookie: `access_token=${token}`,
      },
      cache: 'no-store',
    });

    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}
