import { WEBUI_API_BASE_URL } from '$lib/constants';

// Types
export interface Subsection {
	id: string;
	title: string;
	subtitle: string;
	rag_store_name?: string | null;
}

export interface Section {
	id: string;
	title: string;
	subsections: Subsection[];
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

// POST /api/v1/textbook/sections - 섹션 생성
export const createSection = async (
	token: string,
	title: string
): Promise<Section | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/textbook/sections`, {
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

// PUT /api/v1/textbook/sections/{section_id} - 섹션 수정
export const updateSection = async (
	token: string,
	sectionId: string,
	data: { title?: string }
): Promise<Section | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/textbook/sections/${sectionId}`, {
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

// DELETE /api/v1/textbook/sections/{section_id} - 섹션 삭제
export const deleteSection = async (token: string, sectionId: string): Promise<boolean> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/textbook/sections/${sectionId}`, {
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

// POST /api/v1/textbook/sections/{section_id}/subsections - 서브섹션(챕터) 생성
export const createSubsection = async (
	token: string,
	sectionId: string,
	data: {
		title: string;
		subtitle?: string;
		rag_store_name?: string | null;
	}
): Promise<Subsection | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/textbook/sections/${sectionId}/subsections`, {
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

// PUT /api/v1/textbook/subsections/{subsection_id} - 서브섹션(챕터) 수정
export const updateSubsection = async (
	token: string,
	subsectionId: string,
	data: {
		title?: string;
		subtitle?: string;
		rag_store_name?: string | null;
	}
): Promise<Subsection | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/textbook/subsections/${subsectionId}`, {
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

// DELETE /api/v1/textbook/subsections/{subsection_id} - 서브섹션(챕터) 삭제
export const deleteSubsection = async (token: string, subsectionId: string): Promise<boolean> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/textbook/subsections/${subsectionId}`, {
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
