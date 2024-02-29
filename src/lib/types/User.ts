export type User = {
	role: UserRole;
	id: string;
	email: string;
	name: string;
	profile_image_url: string;
};

export const UserRoles = {};
export type UserRole = keyof typeof UserRoles;
