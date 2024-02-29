export type User = {
	role: UserRole;
	id: string;
	email: string;
	name: string;
	profile_image_url: string;
};

export const UserRoles = {
	pending: 'Pending',
	admin: 'Administrator',
	user: 'User'
};
export type UserRole = keyof typeof UserRoles;
