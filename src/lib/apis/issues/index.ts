import canchatAPI from '$lib/apis/canchatAPI';
import { WEBUI_API_BASE_PATH } from '$lib/constants';

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

	return await canchatAPI(`${WEBUI_API_BASE_PATH}/jira/bug`, {
		method: 'POST',
		data: formData
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			throw new Error(err.message || 'Failed to create issue');
		});
};
