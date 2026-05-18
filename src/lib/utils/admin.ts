export const hasAdminAccess = (user: { role?: string } | null | undefined) =>
	user?.role === 'admin';

export const hasAnalyticsAccess = (
	user: { role?: string; permissions?: { admin?: { analytics?: boolean } } } | null | undefined
) => hasAdminAccess(user) || (user?.permissions?.admin?.analytics ?? false);

export const isAnalyticsOnlyUser = (
	user: { role?: string; permissions?: { admin?: { analytics?: boolean } } } | null | undefined
) => hasAnalyticsAccess(user) && !hasAdminAccess(user);
