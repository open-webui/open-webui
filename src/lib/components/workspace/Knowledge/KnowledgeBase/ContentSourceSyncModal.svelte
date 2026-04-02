<script lang="ts">
	import { createEventDispatcher, getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getContentSourceInfo, syncContentSource } from '$lib/apis/knowledge';
	import { config } from '$lib/stores';
	import Modal from '$lib/components/common/Modal.svelte';
	import type {
		ContentSourceProvider,
		ContentSourceServiceInfo,
		KnowledgeDataWithContentSource
	} from '$lib/types';

	const dispatch = createEventDispatcher<{
		sync: any;
	}>();
	const i18n = getContext('i18n');

	export let show = false;
	export let knowledgeId: string;
	export let provider: ContentSourceProvider;
	export let knowledgeData: KnowledgeDataWithContentSource | null = null;

	let loading: boolean = false;
	let providerInfo: ContentSourceServiceInfo | null = null;
	let sourceId: string = '';
	let syncOptions: Record<string, any> = {};
	let syncIntervalDays: number = 1;

	// Provider-specific configurations
	const providerDefaults: Record<string, any> = {
		google_drive: {
			options: { include_nested: true },
			syncIntervalDays: 1
		},
		onedrive: {
			options: { include_subfolders: true },
			syncIntervalDays: 1
		},
		dropbox: {
			options: { recursive: true },
			syncIntervalDays: 2
		},
		sharepoint: {
			options: { include_subsites: false },
			syncIntervalDays: 1
		}
	};

	// Dev mode sync interval options - applicable to all providers
	$: syncIntervalOptions = [
		...($config?.environment === 'dev' ? [
			{ value: 1/1440, label: '1 minute' },  // 1 minute = 0.000694... days
			{ value: 5/1440, label: '5 minutes' }  // 5 minutes = 0.00347... days
		] : []),
		{ value: 1, label: '1 day' },
		{ value: 2, label: '2 days' },
		{ value: 3, label: '3 days' },
		{ value: 7, label: '1 week' }
	];

	onMount(async () => {
		if (show && provider) {
			await loadProviderInfo();
			loadExistingConfiguration();
		}
	});

	const loadExistingConfiguration = (): void => {
		if (!knowledgeData?.data) return;

		// Check for existing sync metadata from backend
		if (knowledgeData.data?.sync_metadata?.[provider.name]) {
			const syncMeta = knowledgeData.data.sync_metadata[provider.name];
			sourceId = syncMeta.source_id || '';
			const opts = syncMeta.options || {};
			// Extract sync_interval_days from options if it exists there
			syncIntervalDays = opts.sync_interval_days || providerDefaults[provider.name]?.syncIntervalDays || 1;
			// Remove sync_interval_days from options to avoid duplication
			const { sync_interval_days, ...restOptions } = opts;
			syncOptions = restOptions;
		}
		// Apply provider defaults for new configurations
		else if (providerDefaults[provider.name]) {
			syncOptions = { ...providerDefaults[provider.name].options };
			syncIntervalDays = providerDefaults[provider.name].syncIntervalDays;
		}
	};

	// Watch for changes to show prop and reload configuration
	$: if (show && provider) {
		loadProviderInfo();
		loadExistingConfiguration();
	}

	const loadProviderInfo = async (): Promise<void> => {
		try {
			const info = await getContentSourceInfo(localStorage.token, provider.name);
			if (info) {
				providerInfo = info;
			}
		} catch (error) {
			console.error(`Failed to get ${provider.display_name} info:`, error);
			toast.error($i18n.t(`Failed to get ${provider.display_name} configuration`));
		}
	};

	const extractSourceId = (input: string, provider: string): string => {
		// Provider-specific URL extraction patterns
		const patterns: Record<string, RegExp[]> = {
			google_drive: [
				/\/folders\/([a-zA-Z0-9-_]+)/,
				/id=([a-zA-Z0-9-_]+)/,
				/^([a-zA-Z0-9-_]+)$/
			],
			onedrive: [
				/\/folder\/([a-zA-Z0-9-_]+)/,
				/folderid=([a-zA-Z0-9-_]+)/,
				/^([a-zA-Z0-9-_]+)$/
			],
			dropbox: [
				/\/home\/([^?]+)/,
				/path=([^&]+)/,
				/^\/(.+)$/
			],
			sharepoint: [
				/\/sites\/([^\/]+)/,
				/siteid=([a-zA-Z0-9-_]+)/,
				/^([a-zA-Z0-9-_]+)$/
			]
		};

		const providerPatterns = patterns[provider] || [/^(.+)$/];
		
		for (const pattern of providerPatterns) {
			const match = input.match(pattern);
			if (match) {
				return match[1];
			}
		}

		return input; // Return as-is if no pattern matches
	};

	const validateSyncInterval = (interval: number): { valid: boolean; message?: string } => {
		// Validate sync interval is within reasonable bounds
		const MIN_INTERVAL = $config?.environment === 'dev' ? 1/1440 : 0.5; // 1 minute in dev, 12 hours in prod
		const MAX_INTERVAL = 365; // 1 year
		
		if (interval < MIN_INTERVAL) {
			return {
				valid: false,
				message: $config?.environment === 'dev' 
					? 'Sync interval must be at least 1 minute'
					: 'Sync interval must be at least 12 hours'
			};
		}
		
		if (interval > MAX_INTERVAL) {
			return {
				valid: false,
				message: 'Sync interval cannot exceed 365 days'
			};
		}
		
		// Warn about very frequent syncs
		if (interval < 1 && $config?.environment !== 'dev') {
			return {
				valid: true,
				message: 'Warning: Frequent syncs may impact performance and API quotas'
			};
		}
		
		return { valid: true };
	};

	const handleSync = async (): Promise<void> => {
		if (!sourceId.trim()) {
			toast.error($i18n.t(`Please enter a ${provider.display_name} source URL or ID`));
			return;
		}

		// Validate sync interval
		const intervalValidation = validateSyncInterval(syncIntervalDays);
		if (!intervalValidation.valid) {
			toast.error($i18n.t(intervalValidation.message || 'Invalid sync interval'));
			return;
		}
		
		// Show warning for aggressive sync intervals
		if (intervalValidation.message) {
			toast.warning($i18n.t(intervalValidation.message));
		}

		loading = true;

		try {
			const extractedSourceId = extractSourceId(sourceId.trim(), provider.name);
			
			// Validate extracted source ID format
			if (!extractedSourceId || extractedSourceId.length < 3) {
				toast.error($i18n.t('Invalid source ID format'));
				loading = false;
				return;
			}

			const result = await syncContentSource(
				localStorage.token,
				knowledgeId,
				{
					provider: provider.name,
					source_id: extractedSourceId,
					options: {
						...syncOptions,
						sync_interval_days: syncIntervalDays
					}
				}
			);

			if (result) {
				toast.success($i18n.t(`${provider.display_name} synced successfully`));
				dispatch('sync', result);
				show = false;
			} else {
				toast.error($i18n.t(`Failed to sync ${provider.display_name}`));
			}
		} catch (error) {
			console.error('Sync error:', error);
			const errorMessage = error instanceof Error ? error.message : String(error);
			toast.error($i18n.t(`Error syncing ${provider.display_name}: {{error}}`, { error: errorMessage }));
		} finally {
			loading = false;
		}
	};

	const copyToClipboard = (text: string, label: string): void => {
		navigator.clipboard.writeText(text);
		toast.success($i18n.t(`${label} copied to clipboard`));
	};

	// Provider-specific UI helpers
	const getSourcePlaceholder = (provider: string): string => {
		const placeholders: Record<string, string> = {
			google_drive: 'Enter Google Drive folder URL or ID',
			onedrive: 'Enter OneDrive folder URL or ID',
			dropbox: 'Enter Dropbox folder path or link',
			sharepoint: 'Enter SharePoint site URL or ID'
		};
		return placeholders[provider] || 'Enter source URL or ID';
	};

	const getSourceLabel = (provider: string): string => {
		const labels: Record<string, string> = {
			google_drive: 'Folder URL or ID',
			onedrive: 'Folder URL or ID',
			dropbox: 'Folder path or link',
			sharepoint: 'Site URL or ID'
		};
		return labels[provider] || 'Source URL or ID';
	};
</script>

<Modal bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-2">
			<div class=" text-lg font-medium self-center">
				{$i18n.t(`Sync ${provider.display_name}`)}
			</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>
		<hr class=" border-gray-100 dark:border-gray-850" />

		<div class="flex flex-col space-y-4 px-5 pt-4 pb-5">
			<!-- Provider-specific authentication info -->
			{#if providerInfo?.metadata}
				<!-- Service Account Email (Google Drive) -->
				{#if provider.name === 'google_drive' && providerInfo.metadata.service_account_email}
					<div class="space-y-2">
						<div class="text-sm font-medium">
							{$i18n.t('Step 1: Share folder with service account')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400">
							{$i18n.t(
								'Copy the service account email below and share your Google Drive folder with this email address:'
							)}
						</div>
						<div class="flex items-center space-x-2">
							<input
								class="flex-1 text-sm bg-gray-50 dark:bg-gray-850 rounded-lg px-3 py-2"
								type="text"
								value={providerInfo.metadata.service_account_email}
								readonly
							/>
							<button
								class="px-3 py-2 bg-blue-500 hover:bg-blue-600 text-white text-sm rounded-lg"
								on:click={() => copyToClipboard(providerInfo?.metadata?.service_account_email || '', 'Service account email')}
							>
								{$i18n.t('Copy')}
							</button>
						</div>
					</div>
				{/if}

				<!-- OAuth Status (OneDrive, Dropbox) -->
				{#if ['onedrive', 'dropbox'].includes(provider.name) && providerInfo.metadata.oauth_status}
					<div class="space-y-2">
						<div class="text-sm font-medium">
							{$i18n.t('Authentication Status')}
						</div>
						<div class="flex items-center space-x-2">
							{#if providerInfo.metadata.oauth_status === 'connected'}
								<span class="text-green-600 text-sm">✓ {$i18n.t('Connected')}</span>
							{:else}
								<span class="text-yellow-600 text-sm">⚠ {$i18n.t('Not connected')}</span>
								<button
									class="text-blue-500 hover:text-blue-600 text-sm underline"
									on:click={() => {
										// TODO: Implement OAuth flow
										toast.info($i18n.t('OAuth authentication coming soon'));
									}}
								>
									{$i18n.t('Connect Account')}
								</button>
							{/if}
						</div>
					</div>
				{/if}

				<!-- API Key Status (custom providers) -->
				{#if providerInfo.metadata.requires_api_key && !providerInfo.metadata.api_key_configured}
					<div class="space-y-2 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
						<div class="text-sm font-medium text-yellow-800 dark:text-yellow-200">
							{$i18n.t('API Key Required')}
						</div>
						<div class="text-xs text-yellow-700 dark:text-yellow-300">
							{$i18n.t('Please configure the API key in the admin settings before syncing.')}
						</div>
					</div>
				{/if}
			{/if}

			<!-- Source ID/URL Input -->
			<div class="space-y-2">
				<div class="text-sm font-medium">
					{providerInfo?.metadata?.service_account_email 
						? $i18n.t('Step 2: Enter source')
						: $i18n.t('Enter source')}
					: {$i18n.t(getSourceLabel(provider.name))}
				</div>
				<input
					class="w-full text-sm bg-gray-50 dark:bg-gray-850 rounded-lg px-3 py-2"
					type="text"
					placeholder={$i18n.t(getSourcePlaceholder(provider.name))}
					bind:value={sourceId}
				/>
				<div class="text-xs text-gray-500 dark:text-gray-400">
					{$i18n.t(`You can paste the full ${provider.display_name} URL or just the ID`)}
				</div>
			</div>

			<!-- Provider-specific sync options -->
			<div class="space-y-3">
				<div class="text-sm font-medium">{$i18n.t('Sync Options')}</div>

				<!-- Google Drive: Include Nested Folders -->
				{#if provider.name === 'google_drive'}
					<div class="flex items-center space-x-2">
						<input 
							type="checkbox" 
							id="includeNested" 
							bind:checked={syncOptions.include_nested} 
							class="rounded" 
						/>
						<label for="includeNested" class="text-sm">
							{$i18n.t('Include files from nested folders')}
						</label>
					</div>
				{/if}

				<!-- OneDrive: Include Subfolders -->
				{#if provider.name === 'onedrive'}
					<div class="flex items-center space-x-2">
						<input 
							type="checkbox" 
							id="includeSubfolders" 
							bind:checked={syncOptions.include_subfolders} 
							class="rounded" 
						/>
						<label for="includeSubfolders" class="text-sm">
							{$i18n.t('Include files from subfolders')}
						</label>
					</div>
				{/if}

				<!-- Dropbox: Recursive Sync -->
				{#if provider.name === 'dropbox'}
					<div class="flex items-center space-x-2">
						<input 
							type="checkbox" 
							id="recursive" 
							bind:checked={syncOptions.recursive} 
							class="rounded" 
						/>
						<label for="recursive" class="text-sm">
							{$i18n.t('Include all subdirectories')}
						</label>
					</div>
				{/if}

				<!-- SharePoint: Include Subsites -->
				{#if provider.name === 'sharepoint'}
					<div class="flex items-center space-x-2">
						<input 
							type="checkbox" 
							id="includeSubsites" 
							bind:checked={syncOptions.include_subsites} 
							class="rounded" 
						/>
						<label for="includeSubsites" class="text-sm">
							{$i18n.t('Include document libraries from subsites')}
						</label>
					</div>
				{/if}

				<!-- Common: Sync Interval -->
				<div class="space-y-2">
					<label class="text-sm">{$i18n.t('Automatic sync interval')}</label>
					<select
						bind:value={syncIntervalDays}
						class="w-full text-sm bg-gray-50 dark:bg-gray-850 rounded-lg px-3 py-2"
					>
						{#each syncIntervalOptions as option}
							<option value={option.value}>{$i18n.t(option.label)}</option>
						{/each}
					</select>
				</div>

				<!-- Provider-specific additional options could go here -->
			</div>

			<!-- Action Buttons -->
			<div class="flex justify-end space-x-2 pt-4">
				<button
					class="px-4 py-2 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
					on:click={() => {
						show = false;
					}}
				>
					{$i18n.t('Cancel')}
				</button>
				<button
					class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white text-sm rounded-lg disabled:opacity-50"
					disabled={loading || !sourceId.trim()}
					on:click={handleSync}
				>
					{#if loading}
						<div class="flex items-center space-x-2">
							<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
							<span>{$i18n.t('Syncing...')}</span>
						</div>
					{:else}
						{$i18n.t('Sync')}
					{/if}
				</button>
			</div>
		</div>
	</div>
</Modal>