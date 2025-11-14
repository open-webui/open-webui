const TEXT_SCALE_VALUES = [1, 1.1, 1.2, 1.3, 1.4, 1.5] as const;

export type TextScale = (typeof TEXT_SCALE_VALUES)[number];

export const TEXT_SCALE_MIN = TEXT_SCALE_VALUES[0];
export const TEXT_SCALE_MAX = TEXT_SCALE_VALUES[TEXT_SCALE_VALUES.length - 1];

export const DEFAULT_TEXT_SCALE: TextScale = 1;
export const DEFAULT_TEXT_SCALE_INDEX = TEXT_SCALE_VALUES.findIndex(
	(scale) => scale === DEFAULT_TEXT_SCALE
);

export const getScaleFromIndex = (index: number): TextScale => {
	if (!Number.isFinite(index)) {
		return TEXT_SCALE_VALUES[DEFAULT_TEXT_SCALE_INDEX];
	}

	return TEXT_SCALE_VALUES[index] ?? TEXT_SCALE_VALUES[DEFAULT_TEXT_SCALE_INDEX];
};

export const findClosestTextScaleIndex = (value: unknown): number => {
	const numeric = Number(value);

	if (!Number.isFinite(numeric)) {
		return DEFAULT_TEXT_SCALE_INDEX;
	}

	let closestIndex = DEFAULT_TEXT_SCALE_INDEX;
	let smallestDistance = Number.POSITIVE_INFINITY;

	TEXT_SCALE_VALUES.forEach((scale, idx) => {
		const distance = Math.abs(scale - numeric);

		if (distance < smallestDistance) {
			closestIndex = idx;
			smallestDistance = distance;
		}
	});

	return closestIndex;
};

export const resolveTextScale = (value: unknown): TextScale => {
	return TEXT_SCALE_VALUES[findClosestTextScaleIndex(value)] ?? DEFAULT_TEXT_SCALE;
};

export const setDocumentTextScale = (scale: TextScale) => {
	if (typeof document === 'undefined') {
		return;
	}

	document.documentElement.style.setProperty('--app-text-scale', scale.toString());
};

export { TEXT_SCALE_VALUES };
