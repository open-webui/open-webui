import { WEBUI_API_BASE_URL } from '$lib/constants';

export const createNewDoc = async (
	token: string,
	collection_name: string,
	filename: string,
	name: string,
	title: string,
	content: object | null = null
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/documents/create`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			collection_name: collection_name,
			filename: filename,
			name: name,
			title: title,
			...(content ? { content: JSON.stringify(content) } : {})
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getDocs = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/documents/`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getDocByName = async (token: string, name: string) => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('name', name);

	const res = await fetch(`${WEBUI_API_BASE_URL}/documents/docs?${searchParams.toString()}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;

			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

type DocUpdateForm = {
	name: string;
	title: string;
};

export const updateDocByName = async (token: string, name: string, form: DocUpdateForm) => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('name', name);

	const res = await fetch(`${WEBUI_API_BASE_URL}/documents/doc/update?${searchParams.toString()}`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			name: form.name,
			title: form.title
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;

			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

type TagDocForm = {
	name: string;
	tags: string[];
};

export const tagDocByName = async (token: string, name: string, form: TagDocForm) => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('name', name);

	const res = await fetch(`${WEBUI_API_BASE_URL}/documents/doc/tags?${searchParams.toString()}`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			name: form.name,
			tags: form.tags
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;

			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteDocByName = async (token: string, name: string) => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('name', name);

	const res = await fetch(`${WEBUI_API_BASE_URL}/documents/doc/delete?${searchParams.toString()}`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;

			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// Function to call the Self-Aware Document Monitoring API and toggle between enable and disable states
export async function sadmToggleAPISend(token: string, status: boolean) {
    const SADMapiURL = status
        ? `${WEBUI_API_BASE_URL}/sadm/enable`
        : `${WEBUI_API_BASE_URL}/sadm/disable`;

    try {
        const response = await fetch(SADMapiURL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
            },
            body: JSON.stringify({ status }),
        });

        // Check if response is not okay
        if (!response.ok) {
            const errorDetails = await response.text(); // or response.json() if the error response is JSON
            throw new Error(`HTTP error ${response.status}: ${errorDetails}`);
        }

        // Handle successful response
        const data = await response.json();
        console.log('API response:', data);

    } catch (error) {
        // Universal error handling
        if (error instanceof Error) {
            console.error('Error during API request:', error.message);
        } else {
            console.error('Unknown error during API request:', error);
        }
    }
}

// Function to fetch the current status of the Self-Aware Document Monitoring
export async function sadmStatusAPISend(token: string): Promise<string> {
    const STATUS_API_URL = `${WEBUI_API_BASE_URL}/sadm/status`;
    try {
        const response = await fetch(STATUS_API_URL, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
        });

        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}: ${await response.text()}`);
        }

        const data = await response.json();
        return data.status; // "running", "stopped", or "disabled"
    } catch (error) {
        console.error('Error fetching monitoring status:', error);
        throw error;
    }
}	