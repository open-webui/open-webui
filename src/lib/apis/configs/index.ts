import { webuiApiClient } from '../clients';
import type { Banner } from '$lib/types';

// Interfaces
export interface DirectConnectionsConfig extends Record<string, unknown> {}
export interface ToolServerConnection extends Record<string, unknown> {}
export interface CodeExecutionConfig extends Record<string, unknown> {}
export interface ModelsConfig extends Record<string, unknown> {}

// Import/Export Config
export const importConfig = async (token: string, config: Record<string, unknown>) =>
	webuiApiClient.post('/configs/import', { config }, { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to import configuration';
	});

export const exportConfig = async (token: string) =>
	webuiApiClient.get('/configs/export', { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to export configuration';
	});

// Direct Connections Config
export const getDirectConnectionsConfig = async (token: string): Promise<DirectConnectionsConfig> =>
	webuiApiClient
		.get<DirectConnectionsConfig>('/configs/direct_connections', { token })
		.catch((error) => {
			throw error instanceof Error
				? error.message
				: 'Failed to get direct connections configuration';
		});

export const setDirectConnectionsConfig = async (token: string, config: DirectConnectionsConfig) =>
	webuiApiClient.post('/configs/direct_connections', config, { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to set direct connections configuration';
	});

// Tool Server Connections
export const getToolServerConnections = async (token: string): Promise<ToolServerConnection[]> =>
	webuiApiClient.get<ToolServerConnection[]>('/configs/tool_servers', { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to get tool server connections';
	});

export const setToolServerConnections = async (
	token: string,
	connections: ToolServerConnection[]
) =>
	webuiApiClient.post('/configs/tool_servers', connections, { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to set tool server connections';
	});

export const verifyToolServerConnection = async (token: string, connection: ToolServerConnection) =>
	webuiApiClient.post('/configs/tool_servers/verify', connection, { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to verify tool server connection';
	});

// Code Execution Config
export const getCodeExecutionConfig = async (token: string): Promise<CodeExecutionConfig> =>
	webuiApiClient.get<CodeExecutionConfig>('/configs/code_execution', { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to get code execution configuration';
	});

export const setCodeExecutionConfig = async (token: string, config: CodeExecutionConfig) =>
	webuiApiClient.post('/configs/code_execution', config, { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to set code execution configuration';
	});

// Models Config
export const getModelsConfig = async (token: string): Promise<ModelsConfig> =>
	webuiApiClient.get<ModelsConfig>('/configs/models', { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to get models configuration';
	});

export const setModelsConfig = async (token: string, config: ModelsConfig) =>
	webuiApiClient.post('/configs/models', config, { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to set models configuration';
	});

// Prompt Suggestions
export const setDefaultPromptSuggestions = async (token: string, promptSuggestions: string) =>
	webuiApiClient
		.post('/configs/prompt_suggestions', { promptSuggestions }, { token })
		.catch((error) => {
			throw error instanceof Error ? error.message : 'Failed to set default prompt suggestions';
		});

// Banners
export const getBanners = async (token: string): Promise<Banner[]> =>
	webuiApiClient.get<Banner[]>('/configs/banners', { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to get banners';
	});

export const setBanners = async (token: string, banners: Banner[]) =>
	webuiApiClient.post('/configs/banners', { banners }, { token }).catch((error) => {
		throw error instanceof Error ? error.message : 'Failed to set banners';
	});
