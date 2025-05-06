import { WEBUI_API_BASE_URL } from '$lib/constants';

export const deleteAccount = async (token: string): Promise<void> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/users/user/self`, {
		method: 'DELETE',
		headers: {
			Authorization: `Bearer ${token}`,
		},
	});

	if (!res.ok) {
		throw new Error('Error deleting account: request failed');
	}

	const successful = await res.json();

	if (!successful) {
		throw new Error('Error deleting account: delete failed');
	}
};
