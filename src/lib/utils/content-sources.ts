/**
 * Utility functions for content source providers
 */

import type { ContentSourceProvider, KnowledgeDataWithContentSource } from '$lib/types';

// Provider icon SVG paths - these match the paths used in AddContentMenu.svelte
export const providerIcons: Record<string, string> = {
	google_drive: 'M12.01 1.485c-2.082 0-3.754.02-3.743.047.01.02 1.708 3.001 3.774 6.62l3.76 6.574h3.76c2.081 0 3.753-.02 3.742-.047-.005-.02-1.708-3.001-3.775-6.62l-3.76-6.574zm-4.76 1.73a789.828 789.861 0 0 0-3.63 6.319L0 15.868l1.89 3.298 1.885 3.297 3.62-6.335 3.618-6.33-1.88-3.287C8.1 4.704 7.255 3.22 7.25 3.214zm2.259 12.653-.203.348c-.114.198-.96 1.672-1.88 3.287a423.93 423.948 0 0 1-1.698 2.97c-.01.026 3.24.042 7.222.042h7.244l1.796-3.157c.992-1.734 1.85-3.23 1.906-3.323l.104-.167h-7.249z',
	onedrive: 'M12.188 5.813q-1.325 0-2.52.544-1.195.545-2.04 1.565.446.117.85.299.405.181.792.416l4.78 2.86 2.731-1.15q.27-.117.545-.204.276-.088.58-.147-.293-.937-.855-1.705-.563-.768-1.319-1.318-.755-.551-1.658-.856-.902-.304-1.886-.304zM2.414 16.395l9.914-4.184-3.832-2.297q-.586-.351-1.23-.539-.645-.188-1.325-.188-.914 0-1.722.364-.809.363-1.412.978-.603.615-.967 1.424-.363.808-.363 1.722 0 .62.163 1.201.164.58.469 1.09.305.509.738.897.434.387.967.65.533.262 1.13.387.598.126 1.225.126h13.125q.773 0 1.453-.3.68-.299 1.19-.808.51-.51.809-1.19.299-.68.299-1.453 0-.738-.28-1.389-.282-.65-.768-1.136-.486-.486-1.143-.768-.656-.281-1.4-.281h-.047q-.023 0-.047.006-.316-1.242-1.008-2.28-.691-1.036-1.658-1.78-.967-.744-2.144-1.16-1.178-.417-2.456-.417-.949 0-1.845.229-.897.228-1.705.668-.809.439-1.5 1.066-.692.627-1.207 1.413h-.012q-.445.022-.861.082-.416.058-.85.187-.937.293-1.711.861-.774.569-1.324 1.325-.551.755-.862 1.658-.31.902-.31 1.887 0 1.242.474 2.332.475 1.09 1.29 1.904.814.815 1.903 1.29 1.09.475 2.332.475z',
	dropbox: 'M12 5L6 9l6 4-6 4-6-4 6-4L0 5l6-4zm-6 14l6-4 6 4-6 4zm6-6l6-4-6-4 6-4 6 4-6 4 6 4-6 4z',
	sharepoint: 'M24 13.5q0 1.242-.475 2.332-.474 1.09-1.289 1.904-.814.815-1.904 1.29-1.09.474-2.332.474-.762 0-1.523-.2-.106.997-.557 1.858-.451.862-1.154 1.494-.704.633-1.606.99-.902.358-1.91.358-1.09 0-2.045-.416-.955-.416-1.664-1.125-.709-.709-1.125-1.664Q6 19.84 6 18.75q0-.188.018-.375.017-.188.04-.375H.997q-.41 0-.703-.293T0 17.004V6.996q0-.41.293-.703T.996 6h3.54q.14-1.277.726-2.373.586-1.096 1.488-1.904Q7.652.914 8.807.457 9.96 0 11.25 0q1.395 0 2.625.533T16.02 1.98q.914.915 1.447 2.145T18 6.75q0 .188-.012.375-.011.188-.035.375 1.242 0 2.344.469 1.101.468 1.928 1.277.826.809 1.3 1.904Q24 12.246 24 13.5zm-12.75-12q-.973 0-1.857.34-.885.34-1.577.943-.691.604-1.154 1.43Q6.2 5.039 6.06 6h4.945q.41 0 .703.293t.293.703v4.945l.21-.035q.212-.75.61-1.424.399-.673.944-1.218.545-.545 1.213-.944.668-.398 1.43-.61.093-.503.093-.96 0-1.09-.416-2.045-.416-.955-1.125-1.664'
};

/**
 * Get provider icon SVG path
 */
export function getProviderIcon(providerName: string): string | null {
	return providerIcons[providerName] || null;
}

/**
 * Get provider display name with fallback
 */
export function getProviderDisplayName(provider: ContentSourceProvider | string): string {
	if (typeof provider === 'string') {
		// Fallback display names for common providers
		const fallbackNames: Record<string, string> = {
			google_drive: 'Google Drive',
			onedrive: 'OneDrive',
			dropbox: 'Dropbox',
			sharepoint: 'SharePoint'
		};
		return fallbackNames[provider] || provider;
	}
	return provider.display_name || provider.name;
}

/**
 * Check if a knowledge base has content source sync configured
 */
export function hasContentSourceSync(data: KnowledgeDataWithContentSource): boolean {
	// Check both old format (sync_metadata) and new format (content_source)
	if (data.data?.sync_metadata) {
		// Check if any provider has a source_id
		const providers = Object.keys(data.data.sync_metadata);
		return providers.some(provider => 
			data.data.sync_metadata[provider]?.source_id
		);
	}
	return !!data.data?.content_source?.source_id;
}

/**
 * Get the configured content source provider name
 */
export function getConfiguredProvider(data: KnowledgeDataWithContentSource): string | null {
	// Check old format first (sync_metadata)
	if (data.data?.sync_metadata) {
		// Return the first provider that has a source_id
		const providers = Object.keys(data.data.sync_metadata);
		for (const provider of providers) {
			if (data.data.sync_metadata[provider]?.source_id) {
				return provider;
			}
		}
	}
	// Check new format
	return data.data?.content_source?.provider || null;
}

/**
 * Get sync status information
 */
export function getSyncStatus(data: KnowledgeDataWithContentSource): {
	lastSync: number | null;
	intervalDays: number;
	sourceId: string | null;
} {
	// Check old format first (sync_metadata)
	const provider = getConfiguredProvider(data);
	if (provider && data.data?.sync_metadata?.[provider]) {
		const syncData = data.data.sync_metadata[provider];
		return {
			lastSync: syncData.last_sync || null,
			intervalDays: syncData.options?.sync_interval_days || 1,
			sourceId: syncData.source_id || null
		};
	}
	
	// Check new format
	if (data.data?.content_source) {
		return {
			lastSync: data.data.content_source.last_sync || null,
			intervalDays: data.data.content_source.sync_interval_days || 1,
			sourceId: data.data.content_source.source_id || null
		};
	}
	
	return {
		lastSync: null,
		intervalDays: 1,
		sourceId: null
	};
}

/**
 * Format last sync time for display
 */
export function formatLastSync(timestamp: number | null, i18n: any): string {
	if (!timestamp) {
		return i18n.t('Never synced');
	}

	const now = Date.now();
	const diff = now - timestamp * 1000; // Convert to milliseconds
	const minutes = Math.floor(diff / 60000);
	const hours = Math.floor(diff / 3600000);
	const days = Math.floor(diff / 86400000);

	if (minutes < 1) {
		return i18n.t('Just now');
	} else if (minutes < 60) {
		return i18n.t('{{count}} minutes ago', { count: minutes });
	} else if (hours < 24) {
		return i18n.t('{{count}} hours ago', { count: hours });
	} else {
		return i18n.t('{{count}} days ago', { count: days });
	}
}