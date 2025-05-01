import { webuiApiClient } from '../clients';

// Interfaces
export interface ChannelForm {
	name: string;
	data?: Record<string, unknown>;
	meta?: Record<string, unknown>;
	access_control?: Record<string, unknown>;
}

export interface MessageForm {
	parent_id?: string;
	content: string;
	data?: Record<string, unknown>;
	meta?: Record<string, unknown>;
}

// Channel Operations
export const createNewChannel = async (token = '', channel: ChannelForm) =>
	webuiApiClient.post('/channels/create', channel, { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to create new channel';
	});

export const getChannels = async (token = '') =>
	webuiApiClient.get('/channels/', { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to get channels';
	});

export const getChannelById = async (token = '', channel_id: string) =>
	webuiApiClient.get(`/channels/${channel_id}`, { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to get channel';
	});

export const updateChannelById = async (token = '', channel_id: string, channel: ChannelForm) =>
	webuiApiClient.post(`/channels/${channel_id}/update`, channel, { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to update channel';
	});

export const deleteChannelById = async (token = '', channel_id: string) =>
	webuiApiClient.del(`/channels/${channel_id}/delete`, undefined, { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to delete channel';
	});

// Message Operations
export const getChannelMessages = async (token = '', channel_id: string, skip = 0, limit = 50) =>
	webuiApiClient
		.get(`/channels/${channel_id}/messages?skip=${skip}&limit=${limit}`, { token })
		.catch((error) => {
			throw error instanceof Error ? error.message : 'Failed to get channel messages';
		});

export const getChannelThreadMessages = async (
	token = '',
	channel_id: string,
	message_id: string,
	skip = 0,
	limit = 50
) =>
	webuiApiClient
		.get(`/channels/${channel_id}/messages/${message_id}/thread?skip=${skip}&limit=${limit}`, {
			token
		})
		.catch((error) => {
			throw error instanceof Error ? error.message : 'Failed to get thread messages';
		});

export const sendMessage = async (token = '', channel_id: string, message: MessageForm) =>
	webuiApiClient.post(`/channels/${channel_id}/messages`, message, { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to send message';
	});

export const updateMessage = async (
	token = '',
	channel_id: string,
	message_id: string,
	message: MessageForm
) =>
	webuiApiClient
		.post(`/channels/${channel_id}/messages/${message_id}/update`, message, { token })
		.catch((error) => {
			throw error instanceof Error ? error.message : 'Failed to update message';
		});

export const deleteMessage = async (token = '', channel_id: string, message_id: string) =>
	webuiApiClient
		.del(`/channels/${channel_id}/messages/${message_id}/delete`, undefined, { token })
		.catch((error) => {
			throw error instanceof Error ? error.message : 'Failed to delete message';
		});

// Reaction Operations
export const addReaction = async (
	token = '',
	channel_id: string,
	message_id: string,
	name: string
) =>
	webuiApiClient
		.post(`/channels/${channel_id}/messages/${message_id}/reactions/${name}`, undefined, { token })
		.catch((error) => {
			throw error instanceof Error ? error.message : 'Failed to add reaction';
		});

export const removeReaction = async (
	token = '',
	channel_id: string,
	message_id: string,
	name: string
) =>
	webuiApiClient
		.del(`/channels/${channel_id}/messages/${message_id}/reactions/${name}`, undefined, { token })
		.catch((error) => {
			throw error instanceof Error ? error.message : 'Failed to remove reaction';
		});
