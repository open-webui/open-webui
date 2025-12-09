import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface FacilitiesRequest {
	sponsor: string; 
	form_data: Record<string, string>; 
	model: string; 
	web_search_enabled: boolean; 
	files?: any[]; 
}

export interface FacilitiesResponse {
	success: boolean;
	message: string;
	content: string;  // Formatted content for chat display
	sections: Record<string, string>;  // Keep sections for debugging
	sources: Array<{
		source: { id: string; name: string; url?: string };  // Match regular chat format
		document: string[];
		metadata: Array<{ source: string; name: string }>;
		distances?: number[];  // Relevance scores like regular chat
	}>;  // Sources in chat format
	error?: string;
}

export interface ExtractFormDataRequest {
	sponsor: string;
	model: string;
	files: any[];
}

export interface ExtractFormDataResponse {
	success: boolean;
	form_data: Record<string, string>;
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
			if (!res.ok) {
				const errorData = await res.json();
				console.error('Facilities API error response:', errorData);
				throw errorData;
			}
			return res.json();
		})
		.catch((err) => {
			console.error('Facilities API fetch error:', err);
			error = err.detail ?? err.message ?? 'Server connection failed';
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

export const downloadFacilitiesDocument = async (
	token: string,
	sections: Record<string, string>,
	format: 'pdf' | 'doc',
	filename: string,
	removeCitations: boolean = false
): Promise<void> => {
	try {
		const response = await fetch(`${WEBUI_API_BASE_URL}/facilities/download`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			},
			body: JSON.stringify({
				sections: sections,
				format: format,
				filename: filename,
				remove_citations: removeCitations
			})
		});

		if (!response.ok) {
			const errorData = await response.json();
			throw new Error(errorData.detail || 'Failed to download document');
		}

	const blob = await response.blob();

	const url = window.URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	
	const extension = format === 'pdf' ? 'pdf' : format === 'doc' ? 'docx' : 'pdf';
	a.download = `${filename}.${extension}`;

	document.body.appendChild(a);
	a.click();
	document.body.removeChild(a);
	window.URL.revokeObjectURL(url);
	} catch (error: any) {
		console.error('Error downloading facilities document:', error);
		throw error;
	}
};

export const extractFormDataFromFiles = async (
	token: string,
	request: ExtractFormDataRequest
): Promise<ExtractFormDataResponse> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/facilities/extract-form-data`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(request)
	})
		.then(async (res) => {
			if (!res.ok) {
				const errorData = await res.json();
				console.error('Extract form data API error response:', errorData);
				throw errorData;
			}
			return res.json();
		})
		.catch((err) => {
			console.error('Extract form data API fetch error:', err);
			error = err.detail ?? err.message ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
