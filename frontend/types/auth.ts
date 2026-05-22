export type UserRole = 'owner' | 'admin' | 'member' | 'viewer';

export interface TenantSessionUser {
  user_id: string;
  tenant_id: string;
  email: string;
  role: UserRole;
  auth_provider: 'microsoft';
  name?: string | null;
}
