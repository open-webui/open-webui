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

		type Chat = {
			user_id: string;
			title: string;
			updated_at: number;
			created_at: number;
			share_id?: string;
			chat: Record<string, any>;
			archived: boolean;		
		}

		type Message = {
			role: string;
			content: string;
		}

		type Tool = {
			content?: any;
			id?: string;
			name?: string;
			meta?: {
				description: string
			};
		}
		// interface Error {}
		// interface Locals {}
		// interface PageData {}
		// interface Platform {}
	}
}

export {};
