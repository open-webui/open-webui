export const normalizeFolderModelIds = (modelIds: string[]) => {
	const filtered = modelIds.filter((modelId) => modelId !== '');
	return filtered.length > 0 ? filtered : undefined;
};
