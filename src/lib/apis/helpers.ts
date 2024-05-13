// See https://github.com/open-webui/open-webui/pull/2227#issuecomment-2107192913
// for why we're using `any`s here.
/* eslint-disable @typescript-eslint/no-explicit-any */
export function getAPIHeaders(token: string, contentType?: string) {
	const headers: Record<string, string> = {};
	if (token) {
		headers['Authorization'] = `Bearer ${token}`;
	}
	if (contentType) {
		headers['Content-Type'] = contentType;
	}
	return headers;
}

/**
 * Process an API response, throwing an error if the response is not ok.
 */
async function processJSONResponse(res: Response) {
	// We can't use `throw new Error()` here, because these are
	// being passed to e.g. svelte-sonner's `toast.error()`, which can't
	// deal with an `Error` object.
	let content;
	if (res.status === 204) {
		// Do not attempt to decode a `no content` response.
		content = '';
	} else {
		try {
			content = await res.json();
		} catch (e) {
			throw `Failed to parse response as JSON: ${e}`;
		}
	}
	if (!res.ok) {
		if ('detail' in content) {
			throw String(content.detail);
		}
		throw `Request failed with status ${res.status}`;
	}
	return content;
}

/**
 * Make a JSON-bodied request to the API, expecting a JSON response of the shape T.
 */
export async function jsonRequest<T = any>(
	url: string,
	token: string = '',
	bodyJson: unknown,
	method: string = 'POST'
): Promise<T> {
	const res = await fetch(url, {
		method,
		headers: getAPIHeaders(token, 'application/json'),
		body: JSON.stringify(bodyJson)
	});
	return processJSONResponse(res);
}

/**
 * Make a form request to the API, expecting a JSON response of the shape T.
 */
export async function formRequest<T = any>(
	url: string,
	token: string = '',
	body: FormData,
	method: string = 'POST'
): Promise<T> {
	const res = await fetch(url, {
		method,
		headers: getAPIHeaders(token),
		body
	});
	return processJSONResponse(res);
}

/**
 * Make a GET request to the API, expecting a JSON response of the shape T.
 */
export async function getRequest<T = any>(url: string, token: string = ''): Promise<T> {
	const res = await fetch(url, {
		method: 'GET',
		headers: getAPIHeaders(token)
	});
	return processJSONResponse(res);
}

/**
 * Make a body-less DELETE request to the API, expecting a JSON response of the shape T.
 */
export async function deleteRequest<T = any>(url: string, token: string = ''): Promise<T> {
	const res = await fetch(url, {
		method: 'DELETE',
		headers: getAPIHeaders(token, 'application/json')
	});
	return processJSONResponse(res);
}
