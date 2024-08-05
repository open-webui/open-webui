// See https://kit.svelte.dev/docs/types#app
// for information about these interfaces
declare global {
	namespace App {
		type SessionUser = {
			id: string;
			email: string;
			name: string;
			role: string;
			profile_image_url: string;
		};

		type ChatContent = {
			id: string;
			title: string;
			timestamp: number;
			tags: [];
			params: any;
			models: string[];
			messages: Message[];
			history?: History;
		}

		type Chat = {
			user_id: string;
			title: string;
			updated_at: number;
			created_at: number;
			share_id?: string;
			chat: ChatContent;
			archived: boolean;		
		}

		type Message = {
			id: string;
			role: string;
			content: string;
			childrenIds: string[];
			models: string[];
			parentId: string;
			timestamp: number;
			lastSentence?: string;
			context?: string;
			model?: string;
			modelName?: string;
			done?: boolean;
			info?: MessageInfo;
			params?: any;
			tags?: [];
			user?: MessageUser;
			files?: any;
		}

		type MessageInfo = {
			eval_count: number;
			eval_duration: number;
			load_duration: number;
			prompt_eval_count: number;
			prompt_eval_duration: number;
			total_duration: number;
		}

		type MessageUser = {
			info?: {
				meta?: {
					profile_image_url: string;
				}
			}
		}

		type History = {
			messages: { [key:string]: App.Message };
			currentId?: string;
		}

		type Tool = {
			content?: any;
			id?: string;
			name?: string;
			meta?: {
				description: string
			};
		}

		type CompletionChoice = {
			index: number;
			message: {
				role: string;
				content: string;
			},
			finish_reason: string;
		}

		type Completion = {
			id: string;
			object: string;
			created: number;
			model: string;
			system_fingerprint: string;
			choices: CompletionChoice[];
			usage: {
				prompt_tokens: number;
				completion_tokens: number;
				total_tokens: number;
			}
		}

		type ChangelogItem = {
			title: string;
			content: string;
			raw: string;
		}

		type Changelog = {
			[string]: {
				date: string;
				added?: ChangelogItem[];
				fixed?: ChangelogItem[];
				changed?: ChangelogItem[];
				removed?: ChangelogItem[];
			}
		}

		type Model = {
			id: string;
        	name: string;
        	object: string;
        	created: number;
        	owned_by: string;
			ollama?: {
				name: string,
				model: string,
				modified_at: string,
				size: number,
				digest: string
			},
			info?: {
				meta?: {
					position: number;
				},
			},
			actions: []
		}

		type ModelsData = {
			data: Model[]
		}
		// interface Error {}
		// interface Locals {}
		// interface PageData {}
		// interface Platform {}
	}
}

export {};
