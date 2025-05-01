import { webuiApiClient } from '../clients';

export const getGravatarUrl = async (token: string, email: string) =>
	webuiApiClient.get(`/utils/gravatar?email=${email}`, { token });

export const executeCode = async (token: string, code: string) =>
	webuiApiClient.post('/utils/code/execute', { code }, { token });

export const formatPythonCode = async (token: string, code: string) =>
	webuiApiClient.post('/utils/code/format', { code }, { token });

export const downloadChatAsPDF = async (token: string, title: string, messages: object[]) =>
	webuiApiClient
		.post<ArrayBuffer>('/utils/pdf', { title, messages }, { token })
		.then((response) => new Blob([response], { type: 'application/pdf' }));

interface MarkdownResponse {
	html: string;
}

export const getHTMLFromMarkdown = async (token: string, md: string) =>
	webuiApiClient
		.post<MarkdownResponse>('/utils/markdown', { md }, { token })
		.then((response) => response.html);

export const downloadDatabase = async (token: string) => {
	const response = await webuiApiClient.get<ArrayBuffer>('/utils/db/download', { token });
	const blob = new Blob([response], { type: 'application/octet-stream' });
	const url = window.URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = 'webui.db';
	document.body.appendChild(a);
	a.click();
	window.URL.revokeObjectURL(url);
	document.body.removeChild(a);
};

export const downloadLiteLLMConfig = async (token: string) => {
	const response = await webuiApiClient.get<ArrayBuffer>('/utils/litellm/config', { token });
	const blob = new Blob([response], { type: 'application/x-yaml' });
	const url = window.URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = 'config.yaml';
	document.body.appendChild(a);
	a.click();
	window.URL.revokeObjectURL(url);
	document.body.removeChild(a);
};
