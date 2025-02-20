export interface Model {
	id: string;
	name: string;
	object: string;
	created: number;
	owned_by: string;
	max_context_length?: number | null;
	type?: string;
	aliases?: string[];
	openai?: {
		id: string;
		created: number;
		object: string;
		owned_by: string;
		max_context_length?: number | null;
		type?: string;
		aliases?: string[];
	};
	urlIdx?: number;
	info?: {
		id?: string;
		user_id?: string;
		base_model_id?: string | null;
		name?: string;
		params?: Record<string, unknown>;
		meta?: {
			profile_image_url?: string;
			description?: string | null;
			capabilities?: {
				vision?: boolean;
				usage?: boolean;
				citations?: boolean;
			};
			suggestion_prompts?: any | null;
			tags?: Array<{ name: string }>;
		};
		access_control?: {
			read?: {
				group_ids?: string[];
				user_ids?: string[];
			};
			write?: {
				group_ids?: string[];
				user_ids?: string[];
			};
		} | null;
		is_active?: boolean;
		updated_at?: number;
		created_at?: number;
	};
	preset?: boolean;
	actions?: any[];
	arena?: boolean;
}
