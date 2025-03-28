import { WEBUI_API_BASE_URL } from '$lib/constants';

type IncidentItem = {
	email: string;
	description: string;
	stepsToReproduce: string;
	files?: null | FileList;
};

export const createIncident = async (token: string, incident: IncidentItem) => {
	const formData = new FormData();

	formData.append('email', incident.email);
	formData.append('description', incident.description);
	formData.append('stepsToReproduce', incident.stepsToReproduce);

	if (incident.files) {
		Array.from(incident.files).forEach((file) => {
			formData.append('files', file);
		});
	}

	return await fetch(`${WEBUI_API_BASE_URL}/jira/bug`, {
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
				throw new Error(error.detail || 'Failed to create incident');
			}
			return res.json();
		})
		.catch((err) => {
			throw new Error(err.message || 'An unexpected error occurred');
		});
};
