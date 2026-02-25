/**
 * Spaces API - Perplexity-style workspaces with custom instructions, knowledge, and sharing.
 */

import { WEBUI_API_BASE_URL } from '$lib/constants';

// Types
export interface SpaceForm {
	name: string;
	description?: string | null;
	emoji?: string | null;
	instructions?: string | null;
	model_id?: string | null;
	enable_web_by_default?: boolean;
	access_control?: object | null;
}

export interface SpaceUpdateForm {
	name?: string | null;
	description?: string | null;
	emoji?: string | null;
	instructions?: string | null;
	model_id?: string | null;
	enable_web_by_default?: boolean | null;
	access_control?: object | null;
}

export interface SpaceContributor {
	id: string;
	space_id: string;
	user_id: string | null;
	email: string;
	permission: number;
	accepted: boolean;
	user?: {
		id: string;
		name: string;
		email: string;
		profile_image_url?: string;
	} | null;
}

export interface InvitationWithSpace {
	id: string;
	space_id: string;
	email: string;
	permission: number;
	space_name: string;
	space_emoji: string | null;
	space_slug: string;
	created_at: number;
}

// Permission levels (matches backend SpacePermission)
export const SpacePermission = {
	NONE: 0,
	READER: 1,
	WRITER: 2,
	EDITOR: 3,
	OWNER: 4
} as const;

// Access levels (matches backend SpaceAccessLevel)
export const SpaceAccessLevel = {
	PRIVATE: 'private',
	ORG: 'org',
	PUBLIC: 'public'
} as const;

export interface Space {
	id: string;
	user_id: string;
	name: string;
	slug: string;
	description: string | null;
	emoji: string | null;
	instructions: string | null;
	model_id: string | null;
	enable_web_by_default: boolean;
	access_level: string;
	meta: object | null;
	access_control: object | null;
	is_template?: boolean;
	created_at: number;
	updated_at: number;
	user?: object | null;
	knowledge_bases?: object[] | null;
	contributors?: SpaceContributor[] | null;
	user_permission?: number | null;
	write_access?: boolean;
}

export interface SpaceBookmark {
	id: string;
	space_id: string;
	user_id: string;
	created_at: number;
}

export interface SpacePin {
	id: string;
	space_id: string;
	pinned_by: string;
	created_at: number;
}

export interface SpaceCloneForm {
	name: string;
	description?: string | null;
	emoji?: string | null;
}

export interface SpaceLink {
	id: string;
	space_id: string;
	user_id: string;
	url: string;
	title: string | null;
	created_at: number;
}

export interface SpaceSubscription {
	id: string;
	space_id: string;
	user_id: string;
	created_at: number;
}

export interface SpaceNotification {
	id: string;
	space_id: string;
	user_id: string;
	event_type: string;
	event_data: Record<string, unknown> | null;
	read: boolean;
	created_at: number;
	space_name?: string | null;
	space_slug?: string | null;
	space_emoji?: string | null;
}

export interface SpaceListResponse {
	items: Space[];
	total: number;
}

// API Functions

export const getSpaces = async (
	token: string,
	page: number | null = null,
	category: string | null = null
): Promise<SpaceListResponse> => {
	let error = null;

	const searchParams = new URLSearchParams();
	if (page) searchParams.append('page', page.toString());
	if (category) searchParams.append('category', category);

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/?${searchParams.toString()}`, {
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
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const createSpace = async (token: string, form: SpaceForm): Promise<Space> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/create`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(form)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getSpaceById = async (token: string, id: string): Promise<Space> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/${id}`, {
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
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getSpaceBySlug = async (token: string, slug: string): Promise<Space> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/slug/${slug}`, {
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
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateSpaceById = async (
	token: string,
	id: string,
	form: SpaceUpdateForm
): Promise<Space> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/${id}/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(form)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteSpaceById = async (token: string, id: string): Promise<boolean> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/${id}/delete`, {
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
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const addKnowledgeToSpace = async (
	token: string,
	spaceId: string,
	knowledgeId: string
): Promise<Space> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/${spaceId}/knowledge/add`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ knowledge_id: knowledgeId })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const removeKnowledgeFromSpace = async (
	token: string,
	spaceId: string,
	knowledgeId: string
): Promise<Space> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/${spaceId}/knowledge/remove`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ knowledge_id: knowledgeId })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getSpaceKnowledge = async (token: string, spaceId: string): Promise<object[]> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/${spaceId}/knowledge`, {
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
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const inviteContributor = async (
	token: string,
	spaceId: string,
	email: string
): Promise<SpaceContributor> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/${spaceId}/contributors/invite`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ email })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const removeContributor = async (
	token: string,
	spaceId: string,
	email: string
): Promise<boolean> => {
	let error = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/spaces/${spaceId}/contributors/${encodeURIComponent(email)}`,
		{
			method: 'DELETE',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getContributors = async (
	token: string,
	spaceId: string
): Promise<SpaceContributor[]> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/${spaceId}/contributors`, {
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
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getPendingInvitations = async (token: string): Promise<InvitationWithSpace[]> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/invitations/pending`, {
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
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const respondToInvitation = async (
	token: string,
	spaceId: string,
	accept: boolean
): Promise<boolean> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/invitations/${spaceId}/respond`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ accept })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateSpaceAccessLevel = async (
	token: string,
	spaceId: string,
	accessLevel: string
): Promise<Space> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/${spaceId}/access`, {
		method: 'PUT',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ access_level: accessLevel })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// File endpoints

export const uploadFileToSpace = async (
	token: string,
	spaceId: string,
	file: File
): Promise<object> => {
	let error = null;

	const formData = new FormData();
	formData.append('file', file);

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/${spaceId}/files/upload`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			authorization: `Bearer ${token}`
		},
		body: formData
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getSpaceFiles = async (token: string, spaceId: string): Promise<object[]> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/${spaceId}/files`, {
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
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const removeFileFromSpace = async (
	token: string,
	spaceId: string,
	fileId: string
): Promise<boolean> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/${spaceId}/files/${fileId}`, {
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
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// Link endpoints

export const addLinkToSpace = async (
	token: string,
	spaceId: string,
	url: string,
	title?: string
): Promise<SpaceLink> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/${spaceId}/links/add`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ url, title })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getSpaceLinks = async (token: string, spaceId: string): Promise<SpaceLink[]> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/${spaceId}/links`, {
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
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const linkExistingFileToSpace = async (
	token: string,
	spaceId: string,
	fileId: string
): Promise<{ id: string; filename: string; meta: Record<string, unknown>; created_at: number }> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/${spaceId}/files/link`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			file_id: fileId
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail || err.message || 'Failed to link file to space';
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const addSharePointFileToSpace = async (
	token: string,
	spaceId: string,
	tenantId: string,
	driveId: string,
	itemId: string,
	filename?: string
): Promise<{ id: string; filename: string; meta: Record<string, unknown>; created_at: number }> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/${spaceId}/files/sharepoint`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			tenant_id: tenantId,
			drive_id: driveId,
			item_id: itemId,
			filename: filename
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail || err.message || 'Failed to add SharePoint file to space';
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export interface SharePointFolderImportResult {
	added: number;
	skipped: number;
	failed: number;
	files: Array<{ id: string; filename: string; meta: Record<string, unknown> }>;
	errors: string[];
}

/**
 * Import all files from a SharePoint folder to a space (bulk operation)
 * This is more efficient than downloading files one by one
 */
export const addSharePointFolderToSpace = async (
	token: string,
	spaceId: string,
	tenantId: string,
	driveId: string,
	folderId?: string,
	folderName?: string,
	siteName?: string,
	recursive: boolean = true,
	maxDepth: number = 10,
	signal?: AbortSignal
): Promise<SharePointFolderImportResult> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/${spaceId}/files/sharepoint/folder`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			tenant_id: tenantId,
			drive_id: driveId,
			folder_id: folderId,
			folder_name: folderName,
			site_name: siteName,
			recursive: recursive,
			max_depth: maxDepth
		}),
		signal
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail || err.message || 'Failed to import SharePoint folder to space';
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export interface SharePointSyncResult {
	total_checked: number;
	updated: number;
	failed: number;
	up_to_date: number;
	updated_files: Array<{
		id: string;
		filename: string;
		previous_modified_at: string | null;
		current_modified_at: string;
	}>;
	errors: string[];
}

/**
 * Sync SharePoint files in a space - checks for updates and re-downloads changed files
 */
export const syncSharePointFiles = async (
	token: string,
	spaceId: string
): Promise<SharePointSyncResult> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/${spaceId}/files/sharepoint/sync`, {
		method: 'POST',
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
		.catch((err) => {
			error = err.detail || err.message || 'Failed to sync SharePoint files';
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const removeLinkFromSpace = async (
	token: string,
	spaceId: string,
	linkId: string
): Promise<boolean> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/${spaceId}/links/${linkId}`, {
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
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// Bookmark endpoints

export const addBookmark = async (token: string, spaceId: string): Promise<SpaceBookmark> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/bookmarks/add`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ space_id: spaceId })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const removeBookmark = async (token: string, spaceId: string): Promise<boolean> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/bookmarks/${spaceId}`, {
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
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getBookmarkedSpaces = async (token: string): Promise<Space[]> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/bookmarks`, {
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
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// Template endpoints

export const getTemplates = async (token: string): Promise<Space[]> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/templates`, {
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
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const cloneTemplate = async (
	token: string,
	templateId: string,
	form: SpaceCloneForm
): Promise<Space> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/templates/${templateId}/clone`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(form)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// Pin endpoints (admin)

export const addPin = async (token: string, spaceId: string): Promise<SpacePin> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/pins/add`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ space_id: spaceId })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const removePin = async (token: string, spaceId: string): Promise<boolean> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/pins/${spaceId}`, {
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
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getPinnedSpaces = async (token: string): Promise<Space[]> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/pins`, {
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
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// Thread-level sharing

export const updateThreadAccess = async (
	token: string,
	spaceId: string,
	chatId: string,
	accessLevel: string
): Promise<{ chat_id: string; space_id: string; access_level: string }> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/${spaceId}/threads/${chatId}/access`, {
		method: 'PUT',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ access_level: accessLevel })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// Bulk share

export const bulkShareThreads = async (
	token: string,
	spaceId: string
): Promise<{ space_id: string; threads_updated: number }> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/${spaceId}/threads/bulk-share`, {
		method: 'POST',
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
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// Subscription endpoints

export const subscribeToSpace = async (token: string, spaceId: string): Promise<object> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/${spaceId}/subscribe`, {
		method: 'POST',
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
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const unsubscribeFromSpace = async (token: string, spaceId: string): Promise<boolean> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/${spaceId}/subscribe`, {
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
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getSubscriptionStatus = async (
	token: string,
	spaceId: string
): Promise<{ space_id: string; subscribed: boolean }> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/${spaceId}/subscription`, {
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
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// Notification endpoints

export const getUnreadNotifications = async (token: string): Promise<object[]> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/notifications/unread`, {
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
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const markNotificationRead = async (
	token: string,
	notificationId: string
): Promise<boolean> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/notifications/${notificationId}/read`, {
		method: 'POST',
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
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const markAllNotificationsRead = async (token: string): Promise<{ marked_read: number }> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/spaces/notifications/read-all`, {
		method: 'POST',
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
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
