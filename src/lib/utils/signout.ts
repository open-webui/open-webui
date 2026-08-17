export type SignOutResponse = { redirect_url?: string | null } | null;

export const getSignOutRedirect = (response: SignOutResponse) => response?.redirect_url ?? '/auth';

export const shouldPreserveUserForRedirect = (response: SignOutResponse) =>
	Boolean(response?.redirect_url);
