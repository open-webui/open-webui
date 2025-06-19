import { get } from 'svelte/store';
import type { SessionUser } from '$lib/stores';
import { config } from '$lib/stores';

export const buildSurveyUrl = (user: SessionUser): string|null => {
	const surveyUrl = get(config)?.features?.ionos_survey_new_users_url ?? null;

	if (surveyUrl === null) {
		return null;
	}

	if (!user.pseudonymized_user_id) {
		return null;
	}

	const url = new URL(surveyUrl);
	url.searchParams.append('urlVar01', 'DE'); // Country code
	url.searchParams.append('urlVar02', user.pseudonymized_user_id);
	url.searchParams.append('urlVar03', 'Product'); // Channels
	return url.toString();
};
