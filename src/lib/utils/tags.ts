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

export const tagColors = [
	'gray',
	'blue',
	'violet',
	'pink',
	'red',
	'amber',
	'green',
	'teal'
] as const;
export type TagColor = (typeof tagColors)[number];

// A chat tag as folder views show it: with its color and, in filters, how many chats use it.
export type FolderTag = {
	id: string;
	name: string;
	color?: TagColor;
	count?: number;
	meta?: { color?: TagColor } | null;
};

// The tag's chosen color, or a stable default from its id. The palette lives only here.
export const tagColor = (tag: FolderTag): TagColor => {
	const value = tag.color ?? tag.meta?.color;
	return value && tagColors.includes(value)
		? value
		: tagColors[new TextEncoder().encode(tag.id).reduce((a, b) => a + b, 0) % tagColors.length];
};

const tagDots: Record<TagColor, string> = {
	gray: 'bg-gray-400 dark:bg-gray-500',
	blue: 'bg-blue-500',
	violet: 'bg-violet-500',
	pink: 'bg-pink-500',
	red: 'bg-red-500',
	amber: 'bg-amber-500',
	green: 'bg-green-500',
	teal: 'bg-teal-500'
};
export const colorDot = (color: TagColor) => tagDots[color];
export const tagDot = (tag: FolderTag) => tagDots[tagColor(tag)];
