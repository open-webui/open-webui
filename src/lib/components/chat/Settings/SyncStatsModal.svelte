<script lang="ts">
	import { Confetti } from 'svelte-confetti';
	import { toast } from 'svelte-sonner';
	import { getContext, onMount, onDestroy, tick } from 'svelte';

	import { exportChatStats, exportSingleChatStats, downloadChatStats } from '$lib/apis/chats';
	import { getVersion } from '$lib/apis';

	import Modal from '$lib/components/common/Modal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let eventData = null;

	// Listen for verify:chat messages from opener
	const handleMessage = async (event: MessageEvent) => {
		// Community sends: { type: 'verify:chat', data: { id: ... } }
		const chatId = event.data?.data?.id ?? event.data?.id;
		if (event.data?.type === 'verify:chat' && chatId) {
			try {
				const res = await exportSingleChatStats(localStorage.token, chatId);
				if (res && window.opener) {
					window.opener.postMessage(
						{
							type: 'verify:chat:response',
							data: res,
							chatId: chatId,
							requestId: event.data.requestId ?? null
						},
						'*'
					);
				}
			} catch (err: any) {
				console.error('Failed to verify chat:', err);
				if (window.opener) {
					window.opener.postMessage(
						{
							type: 'verify:chat:error',
							error: err?.detail || err?.message || 'Failed to verify chat',
							chatId: chatId,
							requestId: event.data.requestId ?? null
						},
						'*'
					);
				}
			}
		}
	};

	// Watch for modal visibility changes to notify opener
	$: if (show && window.opener) {
		window.opener.postMessage('loaded', '*');
	}

	onMount(() => {
		window.addEventListener('message', handleMessage);
	});

	onDestroy(() => {
		window.removeEventListener('message', handleMessage);
	});

	// State
	let syncing = false;
	let downloading = false;
	let completed = false;
	let error = false;
	let errorMessage = '';

	// Progress tracking
	let processedItemsCount = 0;
	let total = 0;

	// Download controller for cancellation
	let downloadController: AbortController | null = null;

	// Sync mode: 'incremental' or 'full'
	let syncMode: 'incremental' | 'full' = 'incremental';

	// Reactive progress percentage
	$: progressPercent =
		total > 0 ? Math.min(Math.round((processedItemsCount / total) * 100), 100) : 0;

	// Helper to send postMessage to opener
	const postToOpener = (message: object) => {
		if (window.opener) {
			window.opener.postMessage({ ...message, requestId: eventData?.requestId ?? null }, '*');
		}
	};

	// Reset all state
	const resetState = () => {
		syncing = false;
		downloading = false;
		completed = false;
		error = false;
		errorMessage = '';
		processedItemsCount = 0;
		total = 0;
		downloadController = null;
	};

	// Handle error state
	const handleError = (message: string) => {
		console.error('Sync error:', message);
		errorMessage = message;
		error = true;
		syncing = false;
		downloading = false;
		postToOpener({ type: 'sync:error', error: message });
	};

	// Cancel ongoing operations
	const cancelOperation = () => {
		if (downloadController) {
			downloadController.abort();
			downloadController = null;
		}
		syncing = false;
		downloading = false;

		postToOpener({ type: 'sync:error', error: 'User cancelled the operation' });
	};

	// Sync stats to opener window
	const syncStats = async () => {
		if (window.opener) {
			window.opener.focus();
		}
		postToOpener({ type: 'sync:start' });

		syncing = true;
		error = false;
		errorMessage = '';
		processedItemsCount = 0;
		total = 0;

		try {
			// Get version info
			const versionRes = await getVersion(localStorage.token).catch((err) => {
				console.error('Failed to get version:', err);
				return null;
			});

			if (versionRes) {
				postToOpener({ type: 'sync:version', data: versionRes });
			}

			// Paginate through stats
			let page = 1;
			let allItemsLoaded = false;

			while (!allItemsLoaded) {
				// Build search params, include updated_at for incremental mode
				const searchParams = { ...(eventData?.searchParams ?? {}) };
				if (syncMode === 'incremental' && eventData?.lastSyncedChatUpdatedAt) {
					searchParams.updated_at = eventData.lastSyncedChatUpdatedAt;
				}

				const res = await exportChatStats(localStorage.token, page, searchParams).catch((err) => {
					throw new Error(err?.detail || err?.message || 'Failed to export chat stats');
				});

				if (!res) {
					throw new Error('Failed to fetch stats data');
				}

				processedItemsCount += res.items.length;
				total = res.total;

				// Allow UI to repaint
				await tick();

				if (window.opener && res.items.length > 0) {
					postToOpener({ type: 'sync:stats:chats', data: res });
				}

				if (processedItemsCount >= total || res.items.length === 0) {
					allItemsLoaded = true;
				} else {
					page += 1;
				}
			}

			// Success
			postToOpener({ type: 'sync:complete' });
			syncing = false;
			completed = true;
		} catch (err: any) {
			handleError(err?.message || 'An unexpected error occurred');
		}
	};

	// Download stats as JSON file
	const downloadHandler = async () => {
		if (downloading) {
			cancelOperation();
			return;
		}

		downloading = true;
		syncing = true;
		error = false;
		errorMessage = '';
		processedItemsCount = 0;
		total = 0;

		try {
			// Get total count first (no filters for download - get all)
			const initialRes = await exportChatStats(localStorage.token, 1, {}).catch(() => null);

			if (initialRes?.total) {
				total = initialRes.total;
			}

			// Allow UI to show the total
			await tick();

			// Get version for filename
			const versionRes = await getVersion(localStorage.token).catch(() => null);
			const version = versionRes?.version ?? '0.0.0';
			const filename = `open-webui-stats-${version}-${Date.now()}.json`;

			// Start streaming download
			const searchParams = eventData?.searchParams ?? {};
			const [res, controller] = await downloadChatStats(
				localStorage.token,
				searchParams.updated_at
			).catch((err) => {
				throw new Error(
					err?.detail || 'Failed to connect to the server. Please check your connection.'
				);
			});

			if (!res) {
				throw new Error('Failed to start download. The server may be unavailable.');
			}

			downloadController = controller;
			const reader = res.body.getReader();
			const decoder = new TextDecoder();

			const items: any[] = [];
			let buffer = '';

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				buffer += decoder.decode(value, { stream: true });
				const lines = buffer.split('\n');
				buffer = lines.pop() || '';

				for (const line of lines) {
					if (line.trim() !== '') {
						try {
							items.push(JSON.parse(line));
							processedItemsCount += 1;
						} catch (e) {
							console.error('Error parsing line:', e);
						}
					}
				}

				// Allow UI to repaint after each chunk
				await tick();
			}

			// Process remaining buffer
			if (buffer.trim() !== '') {
				try {
					items.push(JSON.parse(buffer));
					processedItemsCount += 1;
				} catch (e) {
					console.error('Error parsing buffer:', e);
				}
			}

			// Trigger download if not cancelled
			if (downloading) {
				const blob = new Blob([JSON.stringify(items)], { type: 'application/json' });
				const url = window.URL.createObjectURL(blob);
				const a = document.createElement('a');
				a.href = url;
				a.download = filename;
				document.body.appendChild(a);
				a.click();
				document.body.removeChild(a);
				window.URL.revokeObjectURL(url);
			}
		} catch (err: any) {
			// Don't show error if user cancelled the download
			if (err?.name === 'AbortError' || err?.message?.includes('aborted')) {
				// User cancelled - just reset state silently
			} else {
				handleError(err?.message || 'Download failed. Please try again.');
				toast.error(errorMessage);
			}
		} finally {
			downloading = false;
			syncing = false;
			downloadController = null;
		}
	};

	// Close modal and reset state
	const closeModal = () => {
		show = false;
		resetState();
	};
</script>

<Modal bind:show size="md">
	<div class="w-full">
		{#if completed}
			<div class="px-5.5 py-5">
				<div class="mb-1 text-xl font-medium">{$i18n.t('Sync Complete!')}</div>
				<div class="mb-3 text-xs text-gray-500">
					{$i18n.t('Your usage stats have been successfully synced.')}
				</div>

				<Confetti x={[-0.5, 0.5]} y={[0.25, 1]} />

				<div class="flex justify-end">
					<button
						class="flex items-center justify-center gap-2 rounded-full bg-black px-4 py-2 text-sm text-white transition hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100"
						on:click={closeModal}
					>
						{$i18n.t('Done')}
					</button>
				</div>
			</div>
		{:else if error}
			<div class="px-5.5 py-5">
				<div class="mb-1 text-xl font-medium">{$i18n.t('Sync Failed')}</div>
				<div class="mb-3 text-xs text-gray-500">
					{errorMessage || $i18n.t('There was an error syncing your stats. Please try again.')}
				</div>

				<div class="flex justify-end">
					<button
						class="flex items-center justify-center gap-2 rounded-full bg-black px-4 py-2 text-sm text-white transition hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100"
						on:click={() => {
							error = false;
							errorMessage = '';
						}}
					>
						{$i18n.t('Try Again')}
					</button>
				</div>
			</div>
		{:else}
			<div class="flex justify-between px-5 pt-4 pb-0.5">
				<div class="text-lg font-medium self-center">{$i18n.t('Sync Usage Stats')}</div>
				<button
					class="self-center"
					on:click={() => {
						show = false;
					}}
					disabled={syncing}
				>
					<XMark className={'size-5'} />
				</button>
			</div>

			<div class="px-5 pt-2 pb-5">
				<div class="text-sm text-gray-500 dark:text-gray-400">
					{$i18n.t('Do you want to sync your usage stats with Open WebUI Community?')}
				</div>

				<div class="mt-2 text-xs text-gray-500">
					{$i18n.t(
						'Participate in community leaderboards and evaluations! Syncing aggregated usage stats helps drive research and improvements to Open WebUI. Your privacy is paramount: no message content is ever shared.'
					)}
				</div>

				<div class="mt-3 text-xs text-gray-500">
					<div class="font-medium text-gray-900 dark:text-gray-100 mb-1">
						{$i18n.t('What is shared:')}
					</div>
					<ul class="list-disc list-inside space-y-0.5 ml-1 mb-2">
						<li>{$i18n.t('Open WebUI version')}</li>
						<li>{$i18n.t('Model names and usage frequency')}</li>
						<li>{$i18n.t('Message counts and response timestamps')}</li>
						<li>{$i18n.t('Content lengths (character counts only)')}</li>
						<li>{$i18n.t('User ratings (thumbs up/down)')}</li>
					</ul>

					<div class="font-medium text-gray-900 dark:text-gray-100 mb-1">
						{$i18n.t('What is NOT shared:')}
					</div>
					<ul class="list-disc list-inside space-y-0.5 ml-1">
						<li>{$i18n.t('Your message text or inputs')}</li>
						<li>{$i18n.t('Model responses or outputs')}</li>
						<li>{$i18n.t('Uploaded files or images')}</li>
					</ul>
				</div>

				{#if eventData?.lastSyncedChatUpdatedAt}
					<div class="mt-3">
						<Tooltip
							content={$i18n.t(
								'Syncs only chats with updates after your last sync timestamp. Disable to re-sync all chats.'
							)}
							placement="top-start"
						>
							<label class="flex items-center gap-2 text-xs cursor-pointer">
								<input
									type="checkbox"
									checked={syncMode === 'incremental'}
									on:change={(e) => (syncMode = e.target.checked ? 'incremental' : 'full')}
									disabled={syncing}
									class="w-4 h-4 rounded border-gray-300 dark:border-gray-600"
								/>
								<span class="text-gray-700 dark:text-gray-300"
									>{$i18n.t('Only sync new/updated chats')}</span
								>
							</label>
						</Tooltip>
					</div>
				{/if}

				{#if syncing}
					<div class="mt-3 mx-1.5">
						<div class="text-xs text-gray-500 mb-1 flex justify-between">
							<div>
								{downloading ? $i18n.t('Downloading stats...') : $i18n.t('Syncing stats...')}
							</div>
							<div>
								{#if total > 0}
									{processedItemsCount}/{total}
								{/if}
							</div>
						</div>
						<div class="w-full bg-gray-200 rounded-full h-1.5 dark:bg-gray-700 overflow-hidden">
							{#if total > 0}
								<div
									class="bg-gray-900 dark:bg-gray-100 h-1.5 rounded-full transition-all duration-300"
									style="width: {progressPercent}%"
								></div>
							{:else}
								<div
									class="bg-gray-900 dark:bg-gray-100 h-1.5 w-0 rounded-full animate-pulse"
								></div>
							{/if}
						</div>
					</div>
				{/if}

				<div class="mt-5 flex justify-between items-center gap-2">
					<div class="text-xs text-gray-400 text-center mr-auto">
						<button
							class="hover:underline px-2"
							type="button"
							on:click={downloadHandler}
							disabled={syncing && !downloading}
						>
							{downloading ? $i18n.t('Stop Download') : $i18n.t('Download as JSON')}
						</button>
					</div>

					<button
						class="px-4 py-2 rounded-full text-sm font-medium bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-900 dark:text-gray-100 transition disabled:cursor-not-allowed"
						on:click={() => {
							if (syncing) {
								cancelOperation();
							} else {
								show = false;
							}
						}}
					>
						{$i18n.t('Cancel')}
					</button>

					<button
						class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition-colors rounded-full"
						on:click={syncStats}
						disabled={syncing}
					>
						{#if syncing && !downloading}
							<div class="flex items-center gap-2">
								<Spinner className="size-3" />
								<span>{$i18n.t('Syncing...')}</span>
							</div>
						{:else}
							{$i18n.t('Sync')}
						{/if}
					</button>
				</div>
			</div>
		{/if}
	</div>
</Modal>
