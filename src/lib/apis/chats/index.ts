import { WEBUI_API_BASE_URL } from '$lib/constants';
import { getTimeRange } from '$lib/utils';
import { handleApiUnauthorized } from '$lib/stores'; // ADDED IMPORT

// Helper function to check token and create headers
const createAuthHeaders = (token: string | null | undefined) => {
    const headers: HeadersInit = {
        Accept: 'application/json',
        'Content-Type': 'application/json'
    };
    // Use lowercase 'authorization' as seen in original code for consistency
    if (token) {
        headers['authorization'] = `Bearer ${token}`;
    }
    return headers;
};


export const createNewChat = async (token: string, chat: object) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/new`, { // Assuming API path is `/chats/new`
        method: 'POST',
        headers: createAuthHeaders(token),
        body: JSON.stringify({
            chat: chat
        })
    })
        .then(async (response) => { // Renamed param
            if (!response.ok) {
                if (response.status === 401) { // ADDED CHECK
                    handleApiUnauthorized();
                    const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                    throw errorBody;
                }
                throw await response.json();
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error creating new chat:`, err);
            // The original used `err` directly, let's try using detail if available
            error = err.detail ?? err ?? 'Failed to create new chat';
            return null;
        });

    if (error && res === null) {
        throw error;
    }

    return res;
};

export const importChat = async (
    token: string,
    chat: object,
    meta: object | null,
    pinned?: boolean,
    folderId?: string | null
) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/import`, { // Assuming API path
        method: 'POST',
        headers: createAuthHeaders(token),
        body: JSON.stringify({
            chat: chat,
            meta: meta ?? {},
            pinned: pinned,
            folder_id: folderId
        })
    })
        .then(async (response) => { // Renamed param
            if (!response.ok) {
                if (response.status === 401) { // ADDED CHECK
                    handleApiUnauthorized();
                    const errorBody = await response.json().catch(() => ({ detail: 'Unauthorized' }));
                    throw errorBody;
                }
                throw await response.json();
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error importing chat:`, err);
            error = err.detail ?? err ?? 'Failed to import chat';
            return null;
        });

    if (error && res === null) {
        throw error;
    }

    return res;
};

// Modified getChatList to use helper and consistent API path from logs
export const getChatList = async (token: string = '', page: number | null = null) => {
    let error = null;
    const searchParams = new URLSearchParams();

    if (page !== null) {
        searchParams.append('page', `${page}`);
    }

    const res = await fetch(`${WEBUI_API_BASE_URL}/api/v1/chats/?${searchParams.toString()}`, { // Path from logs
        method: 'GET',
        headers: createAuthHeaders(token) // Using helper
    })
        .then(async (response) => { // Renamed param
            if (!response.ok) {
                // ADDED CHECK - Special handling for 403 vs 401 based on logs
                // Logs showed 403 Forbidden, which might mean 'not allowed' rather than 'session expired'
                // We only trigger the modal on 401
                if (response.status === 401) {
                    handleApiUnauthorized();
                }
                // Let the original error handling proceed for 403 or other errors
                const errorBody = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw errorBody;
            }
            return response.json();
        })
        // removed intermediate .then((json) => json) as it's redundant
        .catch((err) => {
            console.error(`Error fetching chat list:`, err);
            error = err.detail ?? err ?? 'Failed to fetch chat list';
            return null; // Return null on error
        });

    if (error && res === null) {
        // Check if the thrown error indicates a 401 explicitly, if not, maybe don't throw again?
        // Depends on how the caller handles it. Let's throw for now.
        throw error;
    }

    // If res is null (due to caught error), return empty array otherwise map
    return res ? res.map((chat: any) => ({
        ...chat,
        time_range: getTimeRange(chat.updated_at)
    })) : [];
};


// Apply pattern to all other functions using the token...

export const getChatListByUserId = async (token: string = '', userId: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/list/user/${userId}`, { // Assuming API path
        method: 'GET',
        headers: createAuthHeaders(token)
    })
        .then(async (response) => {
            if (!response.ok) {
                if (response.status === 401) { handleApiUnauthorized(); }
                const errorBody = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw errorBody;
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error fetching chat list by user ID:`, err);
            error = err.detail ?? err ?? 'Failed to fetch chat list by user ID';
            return null;
        });

    if (error && res === null) { throw error; }
    return res ? res.map((chat: any) => ({ ...chat, time_range: getTimeRange(chat.updated_at)	})) : [];
};

export const getArchivedChatList = async (token: string = '') => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/archived`, { // Assuming API path
        method: 'GET',
        headers: createAuthHeaders(token)
    })
        .then(async (response) => {
            if (!response.ok) {
                if (response.status === 401) { handleApiUnauthorized(); }
                const errorBody = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw errorBody;
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error fetching archived chat list:`, err);
            error = err.detail ?? err ?? 'Failed to fetch archived chat list';
            return null;
        });

    if (error && res === null) { throw error; }
    return res;
};

export const getAllChats = async (token: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/all`, { // Assuming API path
        method: 'GET',
        headers: createAuthHeaders(token)
    })
        .then(async (response) => {
            if (!response.ok) {
                if (response.status === 401) { handleApiUnauthorized(); }
                const errorBody = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw errorBody;
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error fetching all chats:`, err);
            error = err.detail ?? err ?? 'Failed to fetch all chats';
            return null;
        });

    if (error && res === null) { throw error; }
    return res;
};

export const getChatListBySearchText = async (token: string, text: string, page: number = 1) => {
    let error = null;

    const searchParams = new URLSearchParams();
    searchParams.append('text', text);
    searchParams.append('page', `${page}`);

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/search?${searchParams.toString()}`, { // Assuming API path
        method: 'GET',
        headers: createAuthHeaders(token)
    })
        .then(async (response) => {
            if (!response.ok) {
                if (response.status === 401) { handleApiUnauthorized(); }
                const errorBody = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw errorBody;
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error searching chats:`, err);
            error = err.detail ?? err ?? 'Failed to search chats';
            return null;
        });

    if (error && res === null) { throw error; }
    return res ? res.map((chat: any) => ({ ...chat, time_range: getTimeRange(chat.updated_at) })) : [];
};

export const getChatsByFolderId = async (token: string, folderId: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/folder/${folderId}`, { // Assuming API path
        method: 'GET',
        headers: createAuthHeaders(token)
    })
        .then(async (response) => {
            if (!response.ok) {
                if (response.status === 401) { handleApiUnauthorized(); }
                const errorBody = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw errorBody;
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error fetching chats by folder ID:`, err);
            error = err.detail ?? err ?? 'Failed to fetch chats by folder ID';
            return null;
        });

    if (error && res === null) { throw error; }
    return res;
};

export const getAllArchivedChats = async (token: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/all/archived`, { // Assuming API path
        method: 'GET',
        headers: createAuthHeaders(token)
    })
        .then(async (response) => {
            if (!response.ok) {
                if (response.status === 401) { handleApiUnauthorized(); }
                const errorBody = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw errorBody;
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error fetching all archived chats:`, err);
            error = err.detail ?? err ?? 'Failed to fetch all archived chats';
            return null;
        });

    if (error && res === null) { throw error; }
    return res;
};

export const getAllUserChats = async (token: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/all/db`, { // Assuming API path
        method: 'GET',
        headers: createAuthHeaders(token)
    })
        .then(async (response) => {
            if (!response.ok) {
                if (response.status === 401) { handleApiUnauthorized(); }
                const errorBody = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw errorBody;
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error fetching all user chats from DB:`, err);
            error = err.detail ?? err ?? 'Failed to fetch all user chats';
            return null;
        });

    if (error && res === null) { throw error; }
    return res;
};

export const getAllTags = async (token: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/all/tags`, { // Assuming API path
        method: 'GET',
        headers: createAuthHeaders(token)
    })
        .then(async (response) => {
            if (!response.ok) {
                if (response.status === 401) { handleApiUnauthorized(); }
                const errorBody = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw errorBody;
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error fetching all tags:`, err);
            error = err.detail ?? err ?? 'Failed to fetch all tags';
            return null;
        });

    if (error && res === null) { throw error; }
    return res;
};


export const getPinnedChatList = async (token: string = '') => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/pinned`, { // Assuming API path
        method: 'GET',
        headers: createAuthHeaders(token)
    })
        .then(async (response) => {
            if (!response.ok) {
                if (response.status === 401) { handleApiUnauthorized(); }
                const errorBody = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw errorBody;
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error fetching pinned chat list:`, err);
            error = err.detail ?? err ?? 'Failed to fetch pinned chat list';
            return null;
        });

    if (error && res === null) { throw error; }
    return res ? res.map((chat: any) => ({ ...chat, time_range: getTimeRange(chat.updated_at) })) : [];
};

export const getChatListByTagName = async (token: string = '', tagName: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/tags`, { // Assuming API path
        method: 'POST',
        headers: createAuthHeaders(token),
        body: JSON.stringify({
            name: tagName
        })
    })
        .then(async (response) => {
            if (!response.ok) {
                if (response.status === 401) { handleApiUnauthorized(); }
                const errorBody = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw errorBody;
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error fetching chat list by tag name:`, err);
            error = err.detail ?? err ?? 'Failed to fetch chat list by tag';
            return null;
        });

    if (error && res === null) { throw error; }
    return res ? res.map((chat: any) => ({ ...chat, time_range: getTimeRange(chat.updated_at) })) : [];
};

export const getChatById = async (token: string, id: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${id}`, { // Assuming API path
        method: 'GET',
        headers: createAuthHeaders(token)
    })
        .then(async (response) => {
            if (!response.ok) {
                if (response.status === 401) { handleApiUnauthorized(); }
                const errorBody = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw errorBody;
            }
            return response.json();
        })
        .catch((err) => {
            // Original catch uses err.detail directly
            console.error(`Error fetching chat by ID:`, err);
            error = err.detail ?? err ?? 'Failed to fetch chat by ID';
            return null;
        });

    if (error && res === null) { throw error; }
    return res;
};

export const getChatByShareId = async (token: string, share_id: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/share/${share_id}`, { // Assuming API path
        method: 'GET',
        headers: createAuthHeaders(token)
    })
        .then(async (response) => {
            if (!response.ok) {
                if (response.status === 401) { handleApiUnauthorized(); }
                const errorBody = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw errorBody;
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error fetching chat by share ID:`, err);
            error = err.detail ?? err ?? 'Failed to fetch chat by share ID';
            return null;
        });

    if (error && res === null) { throw error; }
    return res;
};

export const getChatPinnedStatusById = async (token: string, id: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${id}/pinned`, { // Assuming API path
        method: 'GET',
        headers: createAuthHeaders(token)
    })
        .then(async (response) => {
            if (!response.ok) {
                if (response.status === 401) { handleApiUnauthorized(); }
                const errorBody = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw errorBody;
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error fetching chat pinned status:`, err);
            // Original logic for error extraction
            if ('detail' in err) { error = err.detail;	} else { error = err;}
            return null;
        });

    if (error && res === null) { throw error; }
    return res;
};

export const toggleChatPinnedStatusById = async (token: string, id: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${id}/pin`, { // Assuming API path
        method: 'POST',
        headers: createAuthHeaders(token)
    })
        .then(async (response) => {
            if (!response.ok) {
                if (response.status === 401) { handleApiUnauthorized(); }
                const errorBody = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw errorBody;
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error toggling chat pin status:`, err);
            if ('detail' in err) { error = err.detail;	} else { error = err;}
            return null;
        });

    if (error && res === null) { throw error; }
    return res;
};

export const cloneChatById = async (token: string, id: string, title?: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${id}/clone`, { // Assuming API path
        method: 'POST',
        headers: createAuthHeaders(token),
        body: JSON.stringify({
            ...(title && { title: title })
        })
    })
        .then(async (response) => {
            if (!response.ok) {
                if (response.status === 401) { handleApiUnauthorized(); }
                const errorBody = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw errorBody;
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error cloning chat:`, err);
            if ('detail' in err) { error = err.detail;	} else { error = err;}
            return null;
        });

    if (error && res === null) { throw error; }
    return res;
};

export const cloneSharedChatById = async (token: string, id: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${id}/clone/shared`, { // Assuming API path
        method: 'POST',
        headers: createAuthHeaders(token)
    })
        .then(async (response) => {
            if (!response.ok) {
                if (response.status === 401) { handleApiUnauthorized(); }
                const errorBody = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw errorBody;
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error cloning shared chat:`, err);
            if ('detail' in err) { error = err.detail;	} else { error = err;}
            return null;
        });

    if (error && res === null) { throw error; }
    return res;
};

export const shareChatById = async (token: string, id: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${id}/share`, { // Assuming API path
        method: 'POST',
        headers: createAuthHeaders(token)
    })
        .then(async (response) => {
            if (!response.ok) {
                if (response.status === 401) { handleApiUnauthorized(); }
                const errorBody = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw errorBody;
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error sharing chat:`, err);
            error = err.detail ?? err ?? 'Failed to share chat';
            return null;
        });

    if (error && res === null) { throw error; }
    return res;
};

export const updateChatFolderIdById = async (token: string, id: string, folderId?: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${id}/folder`, { // Assuming API path
        method: 'POST',
        headers: createAuthHeaders(token),
        body: JSON.stringify({
            folder_id: folderId
        })
    })
        .then(async (response) => {
            if (!response.ok) {
                if (response.status === 401) { handleApiUnauthorized(); }
                const errorBody = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw errorBody;
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error updating chat folder ID:`, err);
            error = err.detail ?? err ?? 'Failed to update chat folder';
            return null;
        });

    if (error && res === null) { throw error; }
    return res;
};

export const archiveChatById = async (token: string, id: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${id}/archive`, { // Assuming API path
        method: 'POST',
        headers: createAuthHeaders(token)
    })
        .then(async (response) => {
            if (!response.ok) {
                if (response.status === 401) { handleApiUnauthorized(); }
                const errorBody = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw errorBody;
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error archiving chat:`, err);
            error = err.detail ?? err ?? 'Failed to archive chat';
            return null;
        });

    if (error && res === null) { throw error; }
    return res;
};

export const deleteSharedChatById = async (token: string, id: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${id}/share`, { // Assuming API path
        method: 'DELETE',
        headers: createAuthHeaders(token)
    })
        .then(async (response) => {
            if (!response.ok) {
                if (response.status === 401) { handleApiUnauthorized(); }
                const errorBody = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw errorBody;
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error deleting shared chat:`, err);
            error = err.detail ?? err ?? 'Failed to delete shared chat';
            return null;
        });

    if (error && res === null) { throw error; }
    return res;
};

export const updateChatById = async (token: string, id: string, chat: object) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${id}`, { // Assuming API path
        method: 'POST',
        headers: createAuthHeaders(token),
        body: JSON.stringify({
            chat: chat
        })
    })
        .then(async (response) => {
            if (!response.ok) {
                if (response.status === 401) { handleApiUnauthorized(); }
                const errorBody = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw errorBody;
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error updating chat by ID:`, err);
            error = err.detail ?? err ?? 'Failed to update chat';
            return null;
        });

    if (error && res === null) { throw error; }
    return res;
};

export const deleteChatById = async (token: string, id: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${id}`, { // Assuming API path
        method: 'DELETE',
        headers: createAuthHeaders(token)
    })
        .then(async (response) => {
            if (!response.ok) {
                if (response.status === 401) { handleApiUnauthorized(); }
                const errorBody = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw errorBody;
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error deleting chat by ID:`, err);
            // Original catch uses err.detail directly
            error = err.detail ?? err ?? 'Failed to delete chat';
            return null;
        });

    if (error && res === null) { throw error; }
    return res;
};

export const getTagsById = async (token: string, id: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${id}/tags`, { // Assuming API path
        method: 'GET',
        headers: createAuthHeaders(token)
    })
        .then(async (response) => {
            if (!response.ok) {
                if (response.status === 401) { handleApiUnauthorized(); }
                const errorBody = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw errorBody;
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error fetching tags by ID:`, err);
            error = err.detail ?? err ?? 'Failed to fetch tags';
            return null;
        });

    if (error && res === null) { throw error; }
    return res;
};

export const addTagById = async (token: string, id: string, tagName: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${id}/tags`, { // Assuming API path
        method: 'POST',
        headers: createAuthHeaders(token),
        body: JSON.stringify({
            name: tagName
        })
    })
        .then(async (response) => {
            if (!response.ok) {
                if (response.status === 401) { handleApiUnauthorized(); }
                const errorBody = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw errorBody;
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error adding tag:`, err);
            // Original catch uses err.detail directly
            error = err.detail ?? err ?? 'Failed to add tag';
            return null;
        });

    if (error && res === null) { throw error; }
    return res;
};

export const deleteTagById = async (token: string, id: string, tagName: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${id}/tags`, { // Assuming API path
        method: 'DELETE',
        headers: createAuthHeaders(token),
        body: JSON.stringify({
            name: tagName
        })
    })
        .then(async (response) => {
            if (!response.ok) {
                if (response.status === 401) { handleApiUnauthorized(); }
                const errorBody = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw errorBody;
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error deleting tag:`, err);
            error = err.detail ?? err ?? 'Failed to delete tag';
            return null;
        });

    if (error && res === null) { throw error; }
    return res;
};

export const deleteTagsById = async (token: string, id: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${id}/tags/all`, { // Assuming API path
        method: 'DELETE',
        headers: createAuthHeaders(token)
    })
        .then(async (response) => {
            if (!response.ok) {
                if (response.status === 401) { handleApiUnauthorized(); }
                const errorBody = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw errorBody;
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error deleting all tags for chat:`, err);
            error = err.detail ?? err ?? 'Failed to delete tags';
            return null;
        });

    if (error && res === null) { throw error; }
    return res;
};

export const deleteAllChats = async (token: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/`, { // Assuming API path is /chats/
        method: 'DELETE',
        headers: createAuthHeaders(token)
    })
        .then(async (response) => {
            if (!response.ok) {
                if (response.status === 401) { handleApiUnauthorized(); }
                const errorBody = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw errorBody;
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error deleting all chats:`, err);
            // Original catch uses err.detail directly
            error = err.detail ?? err ?? 'Failed to delete all chats';
            return null;
        });

    if (error && res === null) { throw error; }
    return res;
};

export const archiveAllChats = async (token: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/chats/archive/all`, { // Assuming API path
        method: 'POST',
        headers: createAuthHeaders(token)
    })
        .then(async (response) => {
            if (!response.ok) {
                if (response.status === 401) { handleApiUnauthorized(); }
                const errorBody = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw errorBody;
            }
            return response.json();
        })
        .catch((err) => {
            console.error(`Error archiving all chats:`, err);
            // Original catch uses err.detail directly
            error = err.detail ?? err ?? 'Failed to archive all chats';
            return null;
        });

    if (error && res === null) { throw error; }
    return res;
};
