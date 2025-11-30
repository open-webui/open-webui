<script lang="ts">
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { downloadDatabase } from '$lib/apis/utils';
	import { onMount, getContext } from 'svelte';
	import { config, user } from '$lib/stores';
	import { toast } from 'svelte-sonner';
	import { getAllUserChats } from '$lib/apis/chats';
	import { getAllUsers } from '$lib/apis/users';
	import { exportConfig, importConfig } from '$lib/apis/configs';

	import PruneDataDialog from '$lib/components/common/PruneDataDialog.svelte';
	import { pruneData } from '$lib/apis/prune';
	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let showPruneDataDialog = false;
	let showPreviewResults = false;
	let previewResults = null;
	let lastPruneSettings = null;

	const exportAllUserChats = async () => {
		let blob = new Blob([JSON.stringify(await getAllUserChats(localStorage.token))], {
			type: 'application/json'
		});
		saveAs(blob, `all-chats-export-${Date.now()}.json`);
	};
	
	const handlePruneDataPreview = async (event) => {
		const settings = event.detail;
		lastPruneSettings = settings;

		console.log('Preview call - dry_run should be TRUE');
		const res = await pruneData(
			localStorage.token,
			settings.days,
			settings.exempt_archived_chats,
			settings.exempt_chats_in_folders,
			settings.delete_orphaned_chats,
			settings.delete_orphaned_tools,
			settings.delete_orphaned_functions,
			settings.delete_orphaned_prompts,
			settings.delete_orphaned_knowledge_bases,
			settings.delete_orphaned_models,
			settings.delete_orphaned_notes,
			settings.delete_orphaned_folders,
			settings.audio_cache_max_age_days,
			settings.delete_inactive_users_days,
			settings.exempt_admin_users,
			settings.exempt_pending_users,
			settings.run_vacuum,
			true // dry_run = true for preview
		).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		
		if (res) {
			previewResults = res;
			showPreviewResults = true;
		}
	};

	const handleConfirmPrune = async () => {
		if (!lastPruneSettings) return;

		console.log('Confirm call - dry_run should be FALSE');
		const res = await pruneData(
			localStorage.token,
			lastPruneSettings.days,
			lastPruneSettings.exempt_archived_chats,
			lastPruneSettings.exempt_chats_in_folders,
			lastPruneSettings.delete_orphaned_chats,
			lastPruneSettings.delete_orphaned_tools,
			lastPruneSettings.delete_orphaned_functions,
			lastPruneSettings.delete_orphaned_prompts,
			lastPruneSettings.delete_orphaned_knowledge_bases,
			lastPruneSettings.delete_orphaned_models,
			lastPruneSettings.delete_orphaned_notes,
			lastPruneSettings.delete_orphaned_folders,
			lastPruneSettings.audio_cache_max_age_days,
			lastPruneSettings.delete_inactive_users_days,
			lastPruneSettings.exempt_admin_users,
			lastPruneSettings.exempt_pending_users,
			lastPruneSettings.run_vacuum,
			false // dry_run = false for actual pruning
		).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		
		if (res) {
			toast.success('Data pruned successfully');
			showPreviewResults = false;
			previewResults = null;
			lastPruneSettings = null;
		}
	};

	const exportUsers = async () => {
		const users = await getAllUsers(localStorage.token);

		const headers = ['id', 'name', 'email', 'role'];

		const csv = [
			headers.join(','),
			...users.users.map((user) => {
				return headers
					.map((header) => {
						if (user[header] === null || user[header] === undefined) {
							return '';
						}
						return `"${String(user[header]).replace(/"/g, '""')}"`;
					})
					.join(',');
			})
		].join('\n');

		const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
		saveAs(blob, 'users.csv');
	};

	onMount(async () => {
		// permissions = await getUserPermissions(localStorage.token);
	});
</script>

<!-- Preview Results Modal -->
{#if showPreviewResults && previewResults}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
		<div class="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
			<div class="flex justify-between items-center mb-4">
				<h3 class="text-lg font-medium text-gray-900 dark:text-gray-100">
					{$i18n.t('Pruning Preview Results')}
				</h3>
				<button
					class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
					on:click={() => (showPreviewResults = false)}
				>
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>

			<div class="space-y-4">
				<div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
					<h4 class="text-sm font-medium text-blue-800 dark:text-blue-200 mb-2">
						{$i18n.t('The following items would be deleted:')}
					</h4>
					<div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
						{#if previewResults.inactive_users > 0}
							<div class="flex justify-between">
								<span class="text-gray-700 dark:text-gray-300">{$i18n.t('Inactive users')}:</span>
								<span class="font-medium text-red-600 dark:text-red-400">{previewResults.inactive_users}</span>
							</div>
						{/if}
						{#if previewResults.old_chats > 0}
							<div class="flex justify-between">
								<span class="text-gray-700 dark:text-gray-300">{$i18n.t('Old chats')}:</span>
								<span class="font-medium text-red-600 dark:text-red-400">{previewResults.old_chats}</span>
							</div>
						{/if}
						{#if previewResults.orphaned_chats > 0}
							<div class="flex justify-between">
								<span class="text-gray-700 dark:text-gray-300">{$i18n.t('Orphaned chats')}:</span>
								<span class="font-medium text-red-600 dark:text-red-400">{previewResults.orphaned_chats}</span>
							</div>
						{/if}
						{#if previewResults.orphaned_files > 0}
							<div class="flex justify-between">
								<span class="text-gray-700 dark:text-gray-300">{$i18n.t('Orphaned files')}:</span>
								<span class="font-medium text-red-600 dark:text-red-400">{previewResults.orphaned_files}</span>
							</div>
						{/if}
						{#if previewResults.orphaned_tools > 0}
							<div class="flex justify-between">
								<span class="text-gray-700 dark:text-gray-300">{$i18n.t('Orphaned tools')}:</span>
								<span class="font-medium text-red-600 dark:text-red-400">{previewResults.orphaned_tools}</span>
							</div>
						{/if}
						{#if previewResults.orphaned_functions > 0}
							<div class="flex justify-between">
								<span class="text-gray-700 dark:text-gray-300">{$i18n.t('Orphaned functions')}:</span>
								<span class="font-medium text-red-600 dark:text-red-400">{previewResults.orphaned_functions}</span>
							</div>
						{/if}
						{#if previewResults.orphaned_prompts > 0}
							<div class="flex justify-between">
								<span class="text-gray-700 dark:text-gray-300">{$i18n.t('Orphaned prompts')}:</span>
								<span class="font-medium text-red-600 dark:text-red-400">{previewResults.orphaned_prompts}</span>
							</div>
						{/if}
						{#if previewResults.orphaned_knowledge_bases > 0}
							<div class="flex justify-between">
								<span class="text-gray-700 dark:text-gray-300">{$i18n.t('Orphaned knowledge bases')}:</span>
								<span class="font-medium text-red-600 dark:text-red-400">{previewResults.orphaned_knowledge_bases}</span>
							</div>
						{/if}
						{#if previewResults.orphaned_models > 0}
							<div class="flex justify-between">
								<span class="text-gray-700 dark:text-gray-300">{$i18n.t('Orphaned models')}:</span>
								<span class="font-medium text-red-600 dark:text-red-400">{previewResults.orphaned_models}</span>
							</div>
						{/if}
						{#if previewResults.orphaned_notes > 0}
							<div class="flex justify-between">
								<span class="text-gray-700 dark:text-gray-300">{$i18n.t('Orphaned notes')}:</span>
								<span class="font-medium text-red-600 dark:text-red-400">{previewResults.orphaned_notes}</span>
							</div>
						{/if}
						{#if previewResults.orphaned_folders > 0}
							<div class="flex justify-between">
								<span class="text-gray-700 dark:text-gray-300">{$i18n.t('Orphaned folders')}:</span>
								<span class="font-medium text-red-600 dark:text-red-400">{previewResults.orphaned_folders}</span>
							</div>
						{/if}
						{#if previewResults.orphaned_uploads > 0}
							<div class="flex justify-between">
								<span class="text-gray-700 dark:text-gray-300">{$i18n.t('Orphaned upload files')}:</span>
								<span class="font-medium text-red-600 dark:text-red-400">{previewResults.orphaned_uploads}</span>
							</div>
						{/if}
						{#if previewResults.orphaned_vector_collections > 0}
							<div class="flex justify-between">
								<span class="text-gray-700 dark:text-gray-300">{$i18n.t('Orphaned vector collections')}:</span>
								<span class="font-medium text-red-600 dark:text-red-400">{previewResults.orphaned_vector_collections}</span>
							</div>
						{/if}
						{#if previewResults.audio_cache_files > 0}
							<div class="flex justify-between">
								<span class="text-gray-700 dark:text-gray-300">{$i18n.t('Audio cache files')}:</span>
								<span class="font-medium text-red-600 dark:text-red-400">{previewResults.audio_cache_files}</span>
							</div>
						{/if}
					</div>

					{#if Object.values(previewResults).every(count => count === 0)}
						<div class="text-center py-4">
							<div class="text-green-600 dark:text-green-400 font-medium">
								{$i18n.t('No items would be deleted with current settings')}
							</div>
							<div class="text-sm text-gray-500 dark:text-gray-400 mt-1">
								{$i18n.t('Your system is already clean or no cleanup options are enabled')}
							</div>
						</div>
					{/if}
				</div>

				<!-- Action buttons -->
				<div class="flex justify-end gap-3 pt-4">
					<button
						class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-600 dark:hover:bg-gray-700 transition-colors"
						on:click={() => (showPreviewResults = false)}
					>
						{$i18n.t('Cancel')}
					</button>
					{#if !Object.values(previewResults).every(count => count === 0)}
						<button
							class="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-lg hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
							on:click={handleConfirmPrune}
						>
							{$i18n.t('Prune Data')}
						</button>
					{/if}
				</div>
			</div>
		</div>
	</div>
{/if}

<PruneDataDialog bind:show={showPruneDataDialog} on:preview={handlePruneDataPreview} />
<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={async () => {
		saveHandler();
	}}
>
	<div class=" space-y-3 overflow-y-scroll scrollbar-hidden h-full">
		<div>
			<div class=" mb-2 text-sm font-medium">{$i18n.t('Database')}</div>

			<input
				id="config-json-input"
				hidden
				type="file"
				accept=".json"
				on:change={(e) => {
					const file = e.target.files[0];
					const reader = new FileReader();

					reader.onload = async (e) => {
						const res = await importConfig(localStorage.token, JSON.parse(e.target.result)).catch(
							(error) => {
								toast.error(`${error}`);
							}
						);

						if (res) {
							toast.success($i18n.t('Config imported successfully'));
						}
						e.target.value = null;
					};

					reader.readAsText(file);
				}}
			/>

			<button
				type="button"
				class=" flex rounded-md py-2 px-3 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={async () => {
					document.getElementById('config-json-input').click();
				}}
			>
				<div class=" self-center mr-3">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="w-4 h-4"
					>
						<path d="M2 3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3Z" />
						<path
							fill-rule="evenodd"
							d="M13 6H3v6a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V6ZM8.75 7.75a.75.75 0 0 0-1.5 0v2.69L6.03 9.22a.75.75 0 0 0-1.06 1.06l2.5 2.5a.75.75 0 0 0 1.06 0l2.5-2.5a.75.75 0 1 0-1.06-1.06l-1.22 1.22V7.75Z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
				<div class=" self-center text-sm font-medium">
					{$i18n.t('Import Config from JSON File')}
				</div>
			</button>

			<button
				type="button"
				class=" flex rounded-md py-2 px-3 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={async () => {
					const config = await exportConfig(localStorage.token);
					const blob = new Blob([JSON.stringify(config)], {
						type: 'application/json'
					});
					saveAs(blob, `config-${Date.now()}.json`);
				}}
			>
				<div class=" self-center mr-3">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="w-4 h-4"
					>
						<path d="M2 3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3Z" />
						<path
							fill-rule="evenodd"
							d="M13 6H3v6a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V6ZM8.75 7.75a.75.75 0 0 0-1.5 0v2.69L6.03 9.22a.75.75 0 0 0-1.06 1.06l2.5 2.5a.75.75 0 0 0 1.06 0l2.5-2.5a.75.75 0 1 0-1.06-1.06l-1.22 1.22V7.75Z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
				<div class=" self-center text-sm font-medium">
					{$i18n.t('Export Config to JSON File')}
				</div>
			</button>

			<hr class="border-gray-50 dark:border-gray-850/30 my-1" />

			{#if $config?.features.enable_admin_export ?? true}
				<div class="  flex w-full justify-between">
					<!-- <div class=" self-center text-xs font-medium">{$i18n.t('Allow Chat Deletion')}</div> -->

					<button
						class=" flex rounded-md py-1.5 px-3 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
						type="button"
						on:click={() => {
							// exportAllUserChats();

							downloadDatabase(localStorage.token).catch((error) => {
								toast.error(`${error}`);
							});
						}}
					>
						<div class=" self-center mr-3">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								class="w-4 h-4"
							>
								<path d="M2 3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3Z" />
								<path
									fill-rule="evenodd"
									d="M13 6H3v6a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V6ZM8.75 7.75a.75.75 0 0 0-1.5 0v2.69L6.03 9.22a.75.75 0 0 0-1.06 1.06l2.5 2.5a.75.75 0 0 0 1.06 0l2.5-2.5a.75.75 0 1 0-1.06-1.06l-1.22 1.22V7.75Z"
									clip-rule="evenodd"
								/>
							</svg>
						</div>
						<div class=" self-center text-sm font-medium">{$i18n.t('Download Database')}</div>
					</button>
				</div>

				<button
					class=" flex rounded-md py-2 px-3 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
					on:click={() => {
						exportAllUserChats();
					}}
				>
					<div class=" self-center mr-3">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path d="M2 3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3Z" />
							<path
								fill-rule="evenodd"
								d="M13 6H3v6a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V6ZM8.75 7.75a.75.75 0 0 0-1.5 0v2.69L6.03 9.22a.75.75 0 0 0-1.06 1.06l2.5 2.5a.75.75 0 0 0 1.06 0l2.5-2.5a.75.75 0 1 0-1.06-1.06l-1.22 1.22V7.75Z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<div class=" self-center text-sm font-medium">
						{$i18n.t('Export All Chats (All Users)')}
					</div>
				</button>

				<button
					class=" flex rounded-md py-2 px-3 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
					on:click={() => {
						exportUsers();
					}}
				>
					<div class=" self-center mr-3">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path d="M2 3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3Z" />
							<path
								fill-rule="evenodd"
								d="M13 6H3v6a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V6ZM8.75 7.75a.75.75 0 0 0-1.5 0v2.69L6.03 9.22a.75.75 0 0 0-1.06 1.06l2.5 2.5a.75.75 0 0 0 1.06 0l2.5-2.5a.75.75 0 1 0-1.06-1.06l-1.22 1.22V7.75Z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<div class=" self-center text-sm font-medium">
						{$i18n.t('Export Users')}
					</div>
				</button>
			{/if}
			<hr class="border-gray-100 dark:border-gray-850 my-1" />
			<button
				type="button"
				class=" flex rounded-md py-2 px-3 w-full bg-yellow-500 hover:bg-yellow-600 text-white transition"
				on:click={() => {
					showPruneDataDialog = true;
				}}
			>
				<div class=" self-center mr-3">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="w-4 h-4"
					>
						<path
							fill-rule="evenodd"
							d="M4.5 2a.5.5 0 0 0-.5.5v1a.5.5 0 0 0 .5.5h7a.5.5 0 0 0 .5-.5v-1a.5.5 0 0 0-.5-.5h-7ZM3 6a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V7a1 1 0 0 0-1-1H3Zm1 4a.5.5 0 0 1 .5-.5h6a.5.5 0 0 1 0 1H4.5a.5.5 0 0 1-.5-.5Z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
				<div class=" self-center text-sm font-medium">
					{$i18n.t('Prune Orphaned Data')}
				</div>
			</button>
		</div>
	</div>
</form>
