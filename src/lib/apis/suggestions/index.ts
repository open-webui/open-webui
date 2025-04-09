import { WEBUI_API_BASE_URL } from '$lib/constants';

type SuggestionItem = {
	email: string;
	description: string;
	files?: null | FileList;
};

export const createSuggestion = async (token: string, suggestion: SuggestionItem) => {
	const formData = new FormData();

	formData.append('email', suggestion.email);
	formData.append('description', suggestion.description);

	if (suggestion.files) {
		Array.from(suggestion.files).forEach((file) => {
			formData.append('files', file);
		});
	}

	return await fetch(`${WEBUI_API_BASE_URL}/jira/task`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			authorization: `Bearer ${token}`
		},
		body: formData
	})
		.then(async (res) => {
			if (!res.ok) {
				const error = await res.json();
				throw new Error(error.detail || 'Failed to create suggestion');
			}
			return res.json();
		})
		.catch((err) => {
			throw new Error(err.message || 'An unexpected error occurred');
		});
};
