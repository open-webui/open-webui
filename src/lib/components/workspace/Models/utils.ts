export type ModelKnowledgeItem = {
	collection_name?: string;
	collection_names?: string[];
	id?: string;
	legacy?: boolean;
	name?: string;
	type?: string;
	[key: string]: unknown;
};

export const normalizeModelKnowledge = (items: ModelKnowledgeItem[] = []): ModelKnowledgeItem[] => {
	return items.map((item) => {
		if (item?.collection_name && item?.type !== 'file') {
			return {
				id: item.collection_name,
				name: item.name,
				legacy: true
			};
		} else if (item?.collection_names) {
			return {
				name: item.name,
				type: 'collection',
				collection_names: item.collection_names,
				legacy: false
			};
		} else {
			return item;
		}
	});
};
