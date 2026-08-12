export const resolveImageUrl = (url: string, baseUrl: string): string =>
	url.startsWith('/') ? `${baseUrl}${url}` : url;
