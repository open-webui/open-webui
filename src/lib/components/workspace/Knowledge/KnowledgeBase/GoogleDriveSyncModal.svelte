<script lang="ts">
	import { createEventDispatcher, getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getGoogleDriveServiceAccountEmail, syncGoogleDriveFolder } from '$lib/apis/knowledge';
	import { config } from '$lib/stores';
	import Modal from '$lib/components/common/Modal.svelte';
	import type {
		KnowledgeDataWithGoogleDrive,
		GoogleDriveSyncResponse
	} from '$lib/types/google-drive';

	const dispatch = createEventDispatcher<{
		sync: GoogleDriveSyncResponse;
	}>();
	const i18n = getContext('i18n');

	export let show = false;
	export let knowledgeId: string;
	export let knowledgeData: KnowledgeDataWithGoogleDrive | null = null;

	let loading: boolean = false;
	let serviceAccountEmail: string = '';
	let folderId: string = '';
	let includeNested: boolean = true;
	let syncIntervalDays: number = 1;

	// Note: Backend expects sync_interval_days as a float representing days
	// For dev mode, we convert minutes to fractional days (1 day = 1440 minutes)
	$: syncIntervalOptions = [
		...($config?.environment === 'dev' ? [
			{ value: 1/1440, label: '1 minute' },  // 1 minute = 0.000694... days
			{ value: 5/1440, label: '5 minutes' }  // 5 minutes = 0.00347... days
		] : []),
		{ value: 1, label: '1 day' },
		{ value: 2, label: '2 days' },
		{ value: 3, label: '3 days' }
	];

	onMount(async () => {
		if (show) {
			await loadServiceAccountEmail();
			loadExistingConfiguration();
		}
	});

	const loadExistingConfiguration = (): void => {
		if (knowledgeData) {
			// Load existing Google Drive configuration from knowledge base data
			if (knowledgeData.google_drive_folder_id) {
				folderId = knowledgeData.google_drive_folder_id;
			}
			if (knowledgeData.google_drive_include_nested !== undefined) {
				includeNested = knowledgeData.google_drive_include_nested;
			}
			if (knowledgeData.google_drive_sync_interval_days) {
				syncIntervalDays = knowledgeData.google_drive_sync_interval_days;
			}
		}
	};

	// Watch for changes to show prop and reload configuration
	$: if (show) {
		loadServiceAccountEmail();
		loadExistingConfiguration();
	}

	const loadServiceAccountEmail = async (): Promise<void> => {
		try {
			const response = await getGoogleDriveServiceAccountEmail(localStorage.token);
			if (response?.email) {
				serviceAccountEmail = response.email;
			}
		} catch (error) {
			console.error('Failed to get service account email:', error);
			toast.error($i18n.t('Failed to get Google Drive service account email'));
		}
	};

	const extractFolderIdFromUrl = (url: string): string => {
		// Extract folder ID from Google Drive URL
		const patterns = [/\/folders\/([a-zA-Z0-9-_]+)/, /id=([a-zA-Z0-9-_]+)/, /^([a-zA-Z0-9-_]+)$/];

		for (const pattern of patterns) {
			const match = url.match(pattern);
			if (match) {
				return match[1];
			}
		}

		return url; // Return as-is if no pattern matches
	};

	const handleSync = async (): Promise<void> => {
		if (!folderId.trim()) {
			toast.error($i18n.t('Please enter a Google Drive folder URL or ID'));
			return;
		}

		loading = true;

		try {
			const extractedFolderId = extractFolderIdFromUrl(folderId.trim());

			const result = await syncGoogleDriveFolder(
				localStorage.token,
				knowledgeId,
				extractedFolderId,
				includeNested,
				syncIntervalDays
			);

			if (result) {
				toast.success($i18n.t('Google Drive folder synced successfully'));
				dispatch('sync', result);
				show = false;
			} else {
				toast.error($i18n.t('Failed to sync Google Drive folder'));
			}
		} catch (error) {
			console.error('Sync error:', error);
			const errorMessage = error instanceof Error ? error.message : String(error);
			toast.error($i18n.t('Error syncing Google Drive folder: {{error}}', { error: errorMessage }));
		} finally {
			loading = false;
		}
	};

	const copyServiceAccountEmail = (): void => {
		navigator.clipboard.writeText(serviceAccountEmail);
		toast.success($i18n.t('Service account email copied to clipboard'));
	};
</script>

<Modal bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-2">
			<div class=" text-lg font-medium self-center">{$i18n.t('Sync Google Drive Folder')}</div>
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
			<!-- Service Account Email Section -->
			{#if serviceAccountEmail}
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
							value={serviceAccountEmail}
							readonly
						/>
						<button
							class="px-3 py-2 bg-blue-500 hover:bg-blue-600 text-white text-sm rounded-lg"
							on:click={copyServiceAccountEmail}
						>
							{$i18n.t('Copy')}
						</button>
					</div>
				</div>
			{/if}

			<!-- Folder ID/URL Input -->
			<div class="space-y-2">
				<div class="text-sm font-medium">{$i18n.t('Step 2: Enter folder URL or ID')}</div>
				<input
					class="w-full text-sm bg-gray-50 dark:bg-gray-850 rounded-lg px-3 py-2"
					type="text"
					placeholder={$i18n.t('Enter Google Drive folder URL or ID')}
					bind:value={folderId}
				/>
				<div class="text-xs text-gray-500 dark:text-gray-400">
					{$i18n.t('You can paste the full Google Drive folder URL or just the folder ID')}
				</div>
			</div>

			<!-- Sync Options -->
			<div class="space-y-3">
				<div class="text-sm font-medium">{$i18n.t('Sync Options')}</div>

				<!-- Include Nested Folders -->
				<div class="flex items-center space-x-2">
					<input type="checkbox" id="includeNested" bind:checked={includeNested} class="rounded" />
					<label for="includeNested" class="text-sm">
						{$i18n.t('Include files from nested folders')}
					</label>
				</div>

				<!-- Sync Interval -->
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
					disabled={loading || !folderId.trim()}
					on:click={handleSync}
				>
					{#if loading}
						<div class="flex items-center space-x-2">
							<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
							<span>{$i18n.t('Syncing...')}</span>
						</div>
					{:else}
						{$i18n.t('Sync Folder')}
					{/if}
				</button>
			</div>
		</div>
	</div>
</Modal>
