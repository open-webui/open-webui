import { webuiApiClient } from '../clients';

// Interfaces
export interface AdminConfig extends Record<string, unknown> {}

export interface LdapServerConfig extends Record<string, unknown> {}

export interface UserProfile {
	name: string;
	email: string;
	password: string;
	profile_image_url?: string;
	role?: string;
}

// Admin Operations
export const getAdminDetails = async (token: string) =>
	webuiApiClient.get('/auths/admin/details', { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to get admin details';
	});

export const getAdminConfig = async (token: string): Promise<AdminConfig> =>
	webuiApiClient.get<AdminConfig>('/auths/admin/config', { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to get admin configuration';
	});

export const updateAdminConfig = async (token: string, config: AdminConfig) =>
	webuiApiClient.post('/auths/admin/config', config, { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to update admin configuration';
	});

// Session Operations
export const getSessionUser = async (token: string) =>
	webuiApiClient.get('/auths/', { token, withCredentials: true }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to get session user';
	});

// LDAP Operations
export const ldapUserSignIn = async (user: string, password: string) =>
	webuiApiClient
		.post('/auths/ldap', { user, password }, { withCredentials: true })
		.catch((error) => {
			throw error instanceof Error ? error.message : 'Failed to sign in with LDAP';
		});

export const getLdapConfig = async (token = '') =>
	webuiApiClient.get('/auths/admin/config/ldap', { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to get LDAP configuration';
	});

export const updateLdapConfig = async (token = '', enable_ldap: boolean) =>
	webuiApiClient.post('/auths/admin/config/ldap', { enable_ldap }, { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to update LDAP configuration';
	});

export const getLdapServer = async (token = ''): Promise<LdapServerConfig> =>
	webuiApiClient
		.get<LdapServerConfig>('/auths/admin/config/ldap/server', { token })
		.catch((error) => {
			throw error instanceof Error ? error.message : 'Failed to get LDAP server configuration';
		});

export const updateLdapServer = async (token = '', config: LdapServerConfig) =>
	webuiApiClient.post('/auths/admin/config/ldap/server', config, { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to update LDAP server configuration';
	});

// User Authentication Operations
export const userSignIn = async (email: string, password: string) =>
	webuiApiClient
		.post('/auths/signin', { email, password }, { withCredentials: true })
		.catch((error) => {
			throw error instanceof Error ? error.message : 'Failed to sign in';
		});

export const userSignUp = async (profile: UserProfile) =>
	webuiApiClient.post('/auths/signup', profile, { withCredentials: true }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to sign up';
	});

export const userSignOut = async () =>
	webuiApiClient.get('/auths/signout', { withCredentials: true }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to sign out';
	});

// User Management Operations
export const addUser = async (token: string, profile: UserProfile) =>
	webuiApiClient.post('/auths/add', profile, { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to add user';
	});

export const updateUserProfile = async (token: string, name: string, profileImageUrl: string) =>
	webuiApiClient
		.post('/auths/update/profile', { name, profile_image_url: profileImageUrl }, { token })
		.catch((error) => {
			throw error instanceof Error ? error.message : 'Failed to update user profile';
		});

export const updateUserPassword = async (token: string, password: string, newPassword: string) =>
	webuiApiClient
		.post('/auths/update/password', { password, new_password: newPassword }, { token })
		.catch((error) => {
			throw error instanceof Error ? error.message : 'Failed to update user password';
		});

// Sign Up Configuration
export const getSignUpEnabledStatus = async (token: string) =>
	webuiApiClient.get('/auths/signup/enabled', { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to get sign up enabled status';
	});

export const getDefaultUserRole = async (token: string) =>
	webuiApiClient.get('/auths/signup/user/role', { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to get default user role';
	});

export const updateDefaultUserRole = async (token: string, role: string) =>
	webuiApiClient.post('/auths/signup/user/role', { role }, { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to update default user role';
	});

export const toggleSignUpEnabledStatus = async (token: string) =>
	webuiApiClient.get('/auths/signup/enabled/toggle', { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to toggle sign up enabled status';
	});

// JWT Configuration
export const getJWTExpiresDuration = async (token: string) =>
	webuiApiClient.get('/auths/token/expires', { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to get JWT expires duration';
	});

export const updateJWTExpiresDuration = async (token: string, duration: string) =>
	webuiApiClient.post('/auths/token/expires/update', { duration }, { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to update JWT expires duration';
	});

// API Key Operations
interface ApiKeyResponse {
	api_key: string;
}

export const createAPIKey = async (token: string) =>
	webuiApiClient
		.post<ApiKeyResponse>('/auths/api_key', undefined, { token })
		.then((response) => response.api_key)
		.catch((error) => {
			throw error instanceof Error ? error.message : 'Failed to create API key';
		});

export const getAPIKey = async (token: string) =>
	webuiApiClient
		.get<ApiKeyResponse>('/auths/api_key', { token })
		.then((response) => response.api_key)
		.catch((error) => {
			throw error instanceof Error ? error.message : 'Failed to get API key';
		});

export const deleteAPIKey = async (token: string) =>
	webuiApiClient.del('/auths/api_key', undefined, { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to delete API key';
	});
