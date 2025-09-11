import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface FacilitiesRequest {
	sponsor: string; // "NSF" or "NIH"
	form_data: Record<string, string>; // Section ID -> content mapping
	model: string; // User's selected model ID
	web_search_enabled: boolean; // Whether web search is enabled
}

export interface FacilitiesResponse {
	success: boolean;
	message: string;
	content: string;  // Formatted content for chat display
	sections: Record<string, string>;  // Keep sections for debugging
	sources: Array<{
		source: { id: string; name: string; url?: string };
		document: string[];
		metadata: Array<{ source: string; name: string }>;
	}>;  // Sources in chat format
	error?: string;
}

export const generateFacilitiesResponse = async (
	token: string,
	request: FacilitiesRequest
): Promise<FacilitiesResponse> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/facilities/generate`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(request)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};


export const getFacilitiesSections = async (
	token: string,
	sponsor: string
): Promise<{ success: boolean; sponsor: string; sections: string[] }> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/facilities/sections/${sponsor}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
