// Content Source TypeScript Type Definitions
// Generic types for provider-agnostic content sources
// Mirrors backend Python types for consistency

/**
 * Content source provider information from backend
 */
export interface ContentSourceProvider {
	name: string;
	display_name: string;
	description: string;
	configured: boolean;
	metadata?: Record<string, any>;
}

/**
 * Generic content source sync configuration
 */
export interface ContentSourceSyncConfig {
	provider: string;
	source_id: string;
	options?: Record<string, any>;
}

/**
 * Generic content source sync results
 */
export interface ContentSourceSyncResults {
	added_files: string[];
	updated_files: string[];
	removed_files: string[];
	errors: string[];
}

/**
 * Generic content source file information
 */
export interface ContentSourceFile {
	id: string;
	name: string;
	mimeType: string;
	modifiedTime: string;
	size?: string | number;
	path: string;
	webViewLink?: string;
	provider: string;
	metadata?: Record<string, any>;
}

/**
 * Generic content source folder information
 */
export interface ContentSourceFolder {
	id: string;
	name: string;
	provider: string;
	path?: string;
	metadata?: Record<string, any>;
}

/**
 * Content source service information
 */
export interface ContentSourceServiceInfo {
	provider: string;
	configured: boolean;
	metadata: Record<string, any>;
}

/**
 * Content source sync status
 */
export interface ContentSourceSyncStatus {
	provider: string;
	source_id: string;
	last_sync: number; // Unix timestamp
	sync_interval_days: number;
	status: 'idle' | 'syncing' | 'error';
	error_message?: string;
}

/**
 * Knowledge base data with generic content source fields
 */
export interface KnowledgeDataWithContentSource {
	id?: string;
	name: string;
	description?: string;
	data?: {
		file_ids?: string[];
		// Sync metadata structure
		sync_metadata?: {
			[provider: string]: {
				source_id: string;
				last_sync: number;
				options?: Record<string, any>;
				results?: {
					status: string;
					added: number;
					updated: number;
					failed: number;
					duplicates: number;
					changes: any;
				};
			};
		};
	};
	files?: any[];
}

/**
 * Provider capabilities information
 */
export interface ContentSourceCapabilities {
	supports_folders: boolean;
	supports_recursive_sync: boolean;
	supports_selective_sync: boolean;
	supports_incremental_sync: boolean;
	supports_webhooks: boolean;
	max_file_size?: number;
	supported_mime_types?: string[];
}

/**
 * Content source authentication configuration
 */
export interface ContentSourceAuthConfig {
	type: 'oauth2' | 'api_key' | 'service_account' | 'none';
	oauth2?: {
		client_id: string;
		scopes: string[];
		auth_url?: string;
		token_url?: string;
	};
	api_key?: {
		header_name: string;
		required: boolean;
	};
	service_account?: {
		email: string;
		status: 'active' | 'inactive';
	};
}

/**
 * Helper type guards
 */
export function isContentSourceConfigured(source: ContentSourceProvider): boolean {
	return source.configured;
}

export function hasContentSourceSync(data: KnowledgeDataWithContentSource): boolean {
	return !!data.data?.content_source?.source_id;
}

export function getContentSourceProvider(data: KnowledgeDataWithContentSource): string | undefined {
	if (data.data?.content_source?.provider) {
		return data.data.content_source.provider;
	}
	return undefined;
}