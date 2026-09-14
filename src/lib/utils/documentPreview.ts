export const normalizeDocumentTargetPage = (page: unknown): number | null => {
	if (page === undefined || page === null || page === '') {
		return null;
	}

	const value = Number(page);
	if (!Number.isFinite(value)) {
		return null;
	}

	const targetPage = Math.trunc(value);
	return targetPage > 0 ? targetPage : null;
};

export const clampDocumentTargetPage = (page: number | null | undefined, pageCount: number) => {
	if (!page || pageCount < 1) {
		return null;
	}

	return Math.min(Math.max(1, page), pageCount);
};
