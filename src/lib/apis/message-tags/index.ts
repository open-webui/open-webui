import { WEBUI_API_BASE_URL } from '$lib/constants';

// ============ Types ============

export type MessageTag = {
	id: string;
	chat_id: string;
	message_id: string;
	tag_id: string;
	summary: string | null;
	user_id: string;
	created_at: number;
};

export type TagDefinition = {
	id: string;
	name: string;
	usage_count: number;
	is_protected: boolean;
	meta: object | null;
	created_at: number;
	updated_at: number;
};

export type MessageTagsResponse = {
	tags: MessageTag[];
	definitions: TagDefinition[];
};

export type DaemonConfig = {
	id: string;
	enabled: boolean;
	schedule: 'daily' | 'weekly';
	run_time: string;
	lookback_days: number;
	batch_size: number;
	max_tags: number;
	consolidation_threshold: number;
	custom_tagging_prompt: string | null;
	custom_system_instruction: string | null;
	rag_store_names: string[];
	last_run_at: number | null;
	last_run_status: string | null;
	lock_acquired_at: number | null;
	lock_instance_id: string | null;
	updated_at: number;
};

export type DaemonConfigUpdate = {
	enabled?: boolean;
	schedule?: 'daily' | 'weekly';
	run_time?: string;
	lookback_days?: number;
	batch_size?: number;
	max_tags?: number;
	consolidation_threshold?: number;
	custom_tagging_prompt?: string | null;
	custom_system_instruction?: string | null;
	rag_store_names?: string[];
};

export type TagStats = {
	total_unique_tags: number;
	total_tagged_messages: number;
	max_tags_limit: number;
	last_run_at: number | null;
	last_run_status: string | null;
	daemon_enabled: boolean;
};

export type DaemonProgress = {
	is_running: boolean;
	status: 'idle' | 'collecting' | 'processing' | 'consolidating' | 'completed' | 'error';
	started_at: number | null;
	total_messages: number;
	processed_messages: number;
	current_batch: number;
	total_batches: number;
	progress_percent: number;
	last_error: string | null;
};

export type TagMessageInfo = {
	chat_id: string;
	message_id: string;
	summary: string | null;
	user_name: string;
	created_at: number;
};

export type TagMessagesStats = {
	tag: TagDefinition;
	messages: TagMessageInfo[];
	total_count: number;
	unique_users: number;
};

// ============ User API Functions (declarations only, no UI) ============

/**
 * 메시지 태그 조회
 * GET /message-tags/message/{chat_id}/{message_id}
 */
export const getMessageTags = async (
	token: string,
	chatId: string,
	messageId: string
): Promise<MessageTagsResponse | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/message-tags/message/${chatId}/${messageId}`, {
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

/**
 * 수동 태그 추가
 * POST /message-tags/message/manual
 */
export const addManualTag = async (
	token: string,
	chatId: string,
	messageId: string,
	tagName: string,
	summary?: string
): Promise<MessageTag | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/message-tags/message/manual`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			chat_id: chatId,
			message_id: messageId,
			tag_name: tagName,
			...(summary && { summary })
		})
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

/**
 * 태그 제거
 * DELETE /message-tags/message/{chat_id}/{message_id}/{tag_id}
 */
export const removeMessageTag = async (
	token: string,
	chatId: string,
	messageId: string,
	tagId: string
): Promise<{ success: boolean } | null> => {
	let error = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/message-tags/message/${chatId}/${messageId}/${tagId}`,
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

/**
 * 태그로 메시지 검색
 * GET /message-tags/search/{tag_id}?limit=50
 */
export const searchByTag = async (
	token: string,
	tagId: string,
	limit: number = 50
): Promise<MessageTag[] | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/message-tags/search/${tagId}?limit=${limit}`, {
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

/**
 * 내 태그 목록
 * GET /message-tags/my-tags
 */
export const getMyTags = async (token: string): Promise<TagDefinition[] | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/message-tags/my-tags`, {
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

// ============ Admin API Functions ============

/**
 * 데몬 설정 조회
 * GET /message-tags/admin/config
 */
export const getDaemonConfig = async (token: string): Promise<DaemonConfig | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/message-tags/admin/config`, {
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

/**
 * 데몬 설정 수정
 * PUT /message-tags/admin/config
 */
export const updateDaemonConfig = async (
	token: string,
	config: DaemonConfigUpdate
): Promise<DaemonConfig | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/message-tags/admin/config`, {
		method: 'PUT',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(config)
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

/**
 * 수동 태깅 실행
 * POST /message-tags/admin/run
 */
export const runDaemonManually = async (
	token: string
): Promise<{ status: string; message: string } | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/message-tags/admin/run`, {
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

/**
 * Get daemon progress
 * GET /message-tags/admin/progress
 */
export const getDaemonProgress = async (token: string): Promise<DaemonProgress | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/message-tags/admin/progress`, {
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

/**
 * 전체 태그 목록 (관리자)
 * GET /message-tags/admin/tags
 */
export const getAllTags = async (token: string): Promise<TagDefinition[] | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/message-tags/admin/tags`, {
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

/**
 * 태그 삭제
 * DELETE /message-tags/admin/tags/{tag_id}
 */
export const deleteTag = async (
	token: string,
	tagId: string
): Promise<{ success: boolean } | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/message-tags/admin/tags/${tagId}`, {
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

/**
 * 태그 병합
 * POST /message-tags/admin/tags/merge
 */
export const mergeTags = async (
	token: string,
	keepTagId: string,
	mergeTagIds: string[]
): Promise<{ success: boolean; merged_count: number } | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/message-tags/admin/tags/merge`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			keep_tag_id: keepTagId,
			merge_tag_ids: mergeTagIds
		})
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

/**
 * 태그 이름 변경
 * POST /message-tags/admin/tags/{tag_id}/rename?new_name=xxx
 */
export const renameTag = async (
	token: string,
	tagId: string,
	newName: string
): Promise<TagDefinition | null> => {
	let error = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/message-tags/admin/tags/${tagId}/rename?new_name=${encodeURIComponent(newName)}`,
		{
			method: 'POST',
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

/**
 * 보호 태그 생성
 * POST /message-tags/admin/tags/create
 */
export const createProtectedTag = async (
	token: string,
	name: string,
	isProtected: boolean = true
): Promise<TagDefinition | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/message-tags/admin/tags/create`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			name,
			is_protected: isProtected
		})
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

/**
 * 보호 상태 변경
 * PUT /message-tags/admin/tags/{tag_id}/protection
 */
export const updateTagProtection = async (
	token: string,
	tagId: string,
	isProtected: boolean
): Promise<TagDefinition | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/message-tags/admin/tags/${tagId}/protection`, {
		method: 'PUT',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			is_protected: isProtected
		})
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

/**
 * 통계 조회
 * GET /message-tags/stats
 */
export const getTagStats = async (token: string): Promise<TagStats | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/message-tags/stats`, {
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

// ============ Blacklist API Functions ============

/**
 * 블랙리스트 조회
 * GET /message-tags/admin/blacklist
 */
export const getBlacklist = async (token: string): Promise<string[] | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/message-tags/admin/blacklist`, {
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

/**
 * 블랙리스트에 태그 추가
 * POST /message-tags/admin/blacklist/add
 */
export const addToBlacklist = async (
	token: string,
	tagIds: string[]
): Promise<{ success: boolean } | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/message-tags/admin/blacklist/add`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ tag_ids: tagIds })
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

/**
 * 블랙리스트에서 태그 제거
 * POST /message-tags/admin/blacklist/remove
 */
export const removeFromBlacklist = async (
	token: string,
	tagIds: string[]
): Promise<{ success: boolean } | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/message-tags/admin/blacklist/remove`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ tag_ids: tagIds })
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

// ============ Stats API Functions ============

/**
 * 태그별 메시지 통계 조회
 * GET /message-tags/stats/tag/{tag_id}/messages?limit=10&offset=0
 */
export const getTagMessagesStats = async (
	token: string,
	tagId: string,
	limit: number = 10,
	offset: number = 0
): Promise<TagMessagesStats | null> => {
	let error = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/message-tags/admin/tags/${tagId}/messages?limit=${limit}&offset=${offset}`,
		{
			method: 'GET',
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

/** * Force unlock daemon lock
 * POST /message-tags/admin/unlock
 */
export const unlockDaemon = async (
	token: string
): Promise<{ success: boolean; message: string } | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/message-tags/admin/unlock`, {
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

/** * 상위 N개 태그 조회
 * GET /message-tags/top?limit=10
 */
export const getTopTags = async (
	token: string,
	limit: number = 10
): Promise<TagDefinition[] | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/message-tags/admin/tags/top?limit=${limit}`, {
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
