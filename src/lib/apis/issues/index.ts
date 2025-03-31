import { WEBUI_API_BASE_URL } from '$lib/constants';

type IssueItem = {
	email: string;
	description: string;
	stepsToReproduce: string;
	files?: null | FileList;
};

export const createIssue = async (token: string, issue: IssueItem) => {
	const formData = new FormData();

	formData.append('email', issue.email);
	formData.append('description', issue.description);
	formData.append('stepsToReproduce', issue.stepsToReproduce);

	if (issue.files) {
		Array.from(issue.files).forEach((file) => {
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
				throw new Error(error.detail || 'Failed to create issue');
			}
			return res.json();
		})
		.catch((err) => {
			throw new Error(err.message || 'An unexpected error occurred');
		});
};
