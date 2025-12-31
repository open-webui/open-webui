import { WEBUI_API_BASE_URL } from '$lib/constants';

// Types
export interface Chapter {
	id: string;
	title: string;
	subtitle: string;
	rag_store_name?: string | null;
}

// Admin Chapter with full fields
export interface AdminChapter {
	id: string;
	section_id: string;
	title: string;
	subtitle: string;
	order: number;
	rag_store_name: string | null;
	is_active: boolean;
	created_at: number;
	updated_at: number;
}

export interface Section {
	id: string;
	title: string;
	subsections: Chapter[]; // GET 응답에서는 subsections 사용
}

export interface TextbookData {
	title: string;
	author: string;
	edition: string;
	sections: Section[];
}

// GET /api/v1/textbook/ - 전체 교재 데이터 조회
export const getTextbookData = async (token: string): Promise<TextbookData | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/textbook/`, {
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

// GET /api/v1/textbook/admin/chapters - 모든 챕터 조회 (Admin)
export const getAdminChapters = async (token: string): Promise<AdminChapter[] | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/textbook/admin/chapters`, {
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

// GET /api/v1/textbook/admin/sections - 모든 섹션 조회 (Admin)
export const getAdminSections = async (token: string): Promise<Section[] | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/textbook/admin/sections`, {
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

// POST /api/v1/textbook/admin/sections - 섹션 생성
export const createSection = async (
	token: string,
	title: string
): Promise<Section | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/textbook/admin/sections`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ title })
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

// PUT /api/v1/textbook/admin/sections/{section_id} - 섹션 수정
export const updateSection = async (
	token: string,
	sectionId: string,
	data: { title?: string }
): Promise<Section | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/textbook/admin/sections/${sectionId}`, {
		method: 'PUT',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(data)
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

// DELETE /api/v1/textbook/admin/sections/{section_id} - 섹션 삭제
export const deleteSection = async (token: string, sectionId: string): Promise<boolean> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/textbook/admin/sections/${sectionId}`, {
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

	return res?.success ?? false;
};

// POST /api/v1/textbook/admin/chapters - 챕터 생성
export const createChapter = async (
	token: string,
	data: {
		id: string;
		section_id: string;
		title: string;
		subtitle?: string;
		order?: number;
		rag_store_name?: string | null;
	}
): Promise<AdminChapter | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/textbook/admin/chapters`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(data)
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

// PUT /api/v1/textbook/admin/chapters/{chapter_id} - 챕터 수정
export const updateChapter = async (
	token: string,
	chapterId: string,
	data: {
		section_id?: string;
		title?: string;
		subtitle?: string;
		order?: number;
		is_active?: boolean;
		rag_store_name?: string | null;
	}
): Promise<AdminChapter | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/textbook/admin/chapters/${chapterId}`, {
		method: 'PUT',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(data)
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

// DELETE /api/v1/textbook/admin/chapters/{chapter_id} - 챕터 삭제
export const deleteChapter = async (token: string, chapterId: string): Promise<boolean> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/textbook/admin/chapters/${chapterId}`, {
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

	return res?.success ?? false;
};
