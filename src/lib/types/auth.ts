export interface SessionUser {
	role: string;
	permissions?: {
		chat?: {
			controls?: boolean;
		};
	};
	profile_image_url: string;
}
