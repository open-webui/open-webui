export type Banner = {
	id: string;
	type: string;
	title?: string;
	content: string;
	url?: string;
	dismissible?: boolean;
	timestamp: number;
};

export type PythonScript = {
	id: string;
	name: string;
	description: string;
	content: string;
	user_id: string;
	created_at: string;
	updated_at: string;
	meta: string
}