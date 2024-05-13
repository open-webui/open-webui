export function getAPIHeaders(token: string, contentType?: string) {
	return {
		Accept: 'application/json',
		...(token && { authorization: `Bearer ${token}` }),
		...(contentType && { 'Content-Type': contentType })
	};
}

/**
 * Process an API response, throwing an error if the response is not ok.
 */
async function processResponse(res: Response) {
	const content = await res.json();
	if (!res.ok) {
		if ('detail' in content) {
			throw new Error(content.detail);
		}
		throw new Error(`Request failed with status ${res.status}`);
	}
	return content;
}

/**
 * Make a JSON-bodied request to the API, expecting a JSON response of the shape T.
 */
export async function doJSONRequest<T>(
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
	return processResponse(res);
}

/**
 * Make a form request to the API, expecting a JSON response of the shape T.
 */
export async function doFormRequest<T>(
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
	return processResponse(res);
}

/**
 * Make a GET request to the API, expecting a JSON response of the shape T.
 */
export async function doGetRequest<T>(url: string, token: string = ''): Promise<T> {
	const res = await fetch(url, {
		method: 'GET',
		headers: getAPIHeaders(token)
	});
	return processResponse(res);
}
