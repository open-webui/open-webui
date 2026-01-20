import canchatAPI from '$lib/apis/canchatAPI';
import { WEBUI_API_BASE_PATH } from '$lib/constants';

type SuggestionItem = {
	email: string;
	description: string;
	files?: null | FileList;
};

export const createSuggestion = async (token: string, suggestion: SuggestionItem) => {
	return await canchatAPI(`${WEBUI_API_BASE_PATH}/jira/task`, {
		method: 'POST',
		data: suggestion
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			throw new Error(err.message || 'An unexpected error occurred');
		});
};
