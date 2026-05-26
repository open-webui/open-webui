export const SIDEBAR_CACHE_VERSION = 1;
export const SIDEBAR_CACHE_TTL = 60 * 1000;

export const SIDEBAR_CHANNELS_CACHE_KEY = 'sidebar:channels';
export const SIDEBAR_FOLDERS_CACHE_KEY = 'sidebar:folders';
export const SIDEBAR_TAGS_CACHE_KEY = 'sidebar:tags';
export const SIDEBAR_PINNED_CHATS_CACHE_KEY = 'sidebar:pinned-chats';
export const SIDEBAR_CHATS_CACHE_KEY = 'sidebar:chats:first-page';

export const getSidebarCacheKey = (userId: string | null | undefined, name: string) =>
	JSON.stringify({
		version: SIDEBAR_CACHE_VERSION,
		userId: userId ?? null,
		name
	});
