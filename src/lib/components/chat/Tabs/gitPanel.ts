// Shared look and formatting for the Git panel's views.

export const primaryButton =
	'bg-gray-900 dark:bg-white text-white dark:text-black hover:bg-gray-800 dark:hover:bg-white/90';
export const disabledButton =
	'bg-gray-100 dark:bg-white/6 text-gray-400 dark:text-gray-600 cursor-default';
export const secondaryButton =
	'bg-gray-100 dark:bg-white/6 text-gray-600 dark:text-gray-300 hover:bg-gray-200/60 dark:hover:bg-white/10 disabled:text-gray-400 dark:disabled:text-gray-600 disabled:hover:bg-gray-100 dark:disabled:hover:bg-white/6';

export const relativeTime = (date: string) => {
	const seconds = Math.max(0, Math.floor((Date.now() - new Date(date).getTime()) / 1000));
	return seconds < 60
		? 'now'
		: seconds < 3600
			? `${Math.floor(seconds / 60)}m`
			: seconds < 86400
				? `${Math.floor(seconds / 3600)}h`
				: `${Math.floor(seconds / 86400)}d`;
};

// Pull request and issue lists return at most this many items.
export const LIST_LIMIT = 50;
export const countLabel = (count: number) => (count >= LIST_LIMIT ? `${LIST_LIMIT}+` : `${count}`);
