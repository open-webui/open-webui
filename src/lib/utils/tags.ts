export type Tag = { name: string };

const getTagName = (tag: unknown) => {
	if (typeof tag === 'string') {
		return tag;
	}

	if (typeof tag === 'object' && tag !== null && 'name' in tag) {
		return (tag as { name?: unknown }).name;
	}
};

export const normalizeTags = (tags: unknown): Tag[] =>
	(Array.isArray(tags) ? tags : [])
		.map(getTagName)
		.filter((name): name is string => typeof name === 'string' && name.trim() !== '')
		.map((name) => ({ name: name.trim() }));
