import { PUBLIC_PROCONNECT_BASE_URL } from '$env/static/public';

interface UserInfo {
	given_name?: string;
	usual_name?: string;
	email?: string;
	sub?: string;
	[key: string]: any;
}

export const proconnectService = {
	login: () => {
		window.location.href = `${PUBLIC_PROCONNECT_BASE_URL}/api/v2/login`;
	},

	logout: async () => {
		try {
			const response = await fetch(`${PUBLIC_PROCONNECT_BASE_URL}/api/v2/prepare-logout`);
			if (response.ok) {
				const data = await response.json();
				if (data.url) {
					window.location.href = data.url;
				}
			} else {
				throw new Error('Logout failed');
			}
		} catch (error) {
			console.error('Error during logout:', error);
			throw error;
		}
	},

	getUserInfo: async (): Promise<UserInfo | null> => {
		try {
			const response = await fetch(`${PUBLIC_PROCONNECT_BASE_URL}/api/v2/protected`);
			if (response.ok) {
				const data = await response.json();
				return data.user;
			}
			return null;
		} catch (error) {
			console.error('Error fetching user info:', error);
			return null;
		}
	},

	checkAuthStatus: async (): Promise<boolean> => {
		try {
			const response = await fetch(`${PUBLIC_PROCONNECT_BASE_URL}/api/v2/protected`);
			return response.ok;
		} catch (error) {
			return false;
		}
	}
};
