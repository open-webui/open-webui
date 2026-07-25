export type KnowledgeStats = {
	file_count?: number;
	directory_count?: number;
	total_size?: number;
};

export type KnowledgeMeta = {
	stats?: KnowledgeStats;
	statistics_outdated?: boolean;
} | null;

/**
 * Flag a knowledge base's cached stats as outdated — locally, no backend call.
 *
 * Used after adding/deleting a file or folder: the exact numbers aren't
 * recomputed client-side, we just mark them stale so the UI can show an
 * "(outdated)" hint until the user refreshes.
 *
 * Returns a new object when stats exist (so Svelte reactivity fires) and the
 * SAME reference (a no-op) when there are no stats to invalidate.
 */
export const withStatsOutdated = <T extends Record<string, any>>(knowledge: T): T => {
	if (!knowledge?.meta?.stats) return knowledge;
	return { ...knowledge, meta: { ...(knowledge.meta ?? {}), statistics_outdated: true } };
};
