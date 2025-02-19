import { writable } from 'svelte/store';

interface User {
	given_name?: string;
	usual_name?: string;
	email?: string;
	sub?: string;
	[key: string]: any;
}

export const user = writable<User | null>(null);
export const isAuthenticated = writable<boolean>(false);

export const clearAuth = () => {
	user.set(null);
	isAuthenticated.set(false);
};

export const setAuth = (userData: User) => {
	user.set(userData);
	isAuthenticated.set(true);
};
