import { WEBUI_API_BASE_URL } from '$lib/constants';

export type ExternalVolume = {
	name: string;
	primary: string;
	fallback: string;
	mount: string;
};

export type ExternalVolumesConfig = {
	volumes: ExternalVolume[];
};

export type VolumeStatus = {
	name: string;
	primary: string;
	fallback: string;
	mount: string;
	is_available: boolean;
	marker_exists: boolean;
};

export type ExclusionsConfig = {
	excludes: string[];
	path?: string;
};

const handleResponse = async (res: Response) => {
	if (!res.ok) {
		throw await res.json();
	}
	return res.json();
};

export const getExternalVolumes = async (token: string) => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/rag/volumes`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});
	return handleResponse(res) as Promise<ExternalVolumesConfig>;
};

export const getVolumesStatus = async (token: string) => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/rag/volumes/status`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});
	return handleResponse(res) as Promise<VolumeStatus[]>;
};

export const updateExternalVolumes = async (token: string, config: ExternalVolumesConfig) => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/rag/volumes`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify(config)
	});
	return handleResponse(res);
};

export const markVolumeAvailable = async (token: string, volumeName: string) => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/rag/volumes/${volumeName}/mark-available`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});
	return handleResponse(res);
};

export const getExclusions = async (token: string) => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/rag/exclusions`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});
	return handleResponse(res) as Promise<ExclusionsConfig>;
};

export const updateExclusions = async (token: string, config: ExclusionsConfig) => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/rag/exclusions`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify(config)
	});
	return handleResponse(res);
};
