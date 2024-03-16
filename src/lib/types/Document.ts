export type Document = {
	collection_name: string;
	filename: string;
	name: string;
	content?: DocumentContent;
	title: string;
	type?: 'collection';
	collection_names?: string[];
};

export type DocumentContent = {
	tags: DocumentContentTag[];
};

export type DocumentContentTag = {
	name: string;
};
