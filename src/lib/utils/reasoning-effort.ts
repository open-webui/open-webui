export const parseReasoningEffortOptions = (raw: unknown): string[] => {
	if (typeof raw !== 'string') {
		return [];
	}

	return [
		...new Set(
			raw
				.split(',')
				.map((option) => option.trim())
				.filter((option) => option !== '')
		)
	];
};
