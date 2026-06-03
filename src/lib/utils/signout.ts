import { userSignOut } from '$lib/apis/auths';
import { user } from '$lib/stores';

type SignOutResponse = {
	redirect_url?: string;
} | null;

export const resolveSignOutRedirect = (res: SignOutResponse) => {
	return res?.redirect_url ?? '/auth';
};

export const performSignOut = async () => {
	const res = await userSignOut();
	user.set(null);
	localStorage.removeItem('token');
	location.href = resolveSignOutRedirect(res);
	return res;
};
