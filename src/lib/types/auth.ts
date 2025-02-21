export interface SessionUser {
	role: string;
	permissions?: {
		workspace?: {
			models?: boolean;
			knowledge?: boolean;
			prompts?: boolean;
			tools?: boolean;
		};
		chat?: {
			controls?: boolean;
			file_upload?: boolean;
			delete?: boolean;
			edit?: boolean;
			temporary?: boolean;
		};
		features?: {
			web_search?: boolean;
			image_generation?: boolean;
			code_interpreter?: boolean;
		};
	};
	profile_image_url: string;
	token?: string;
	email?: string;
	name?: string;
	id?: string;
	auth_type?: string;
}
