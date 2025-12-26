<script lang="ts">
	import { Confetti } from 'svelte-confetti';

	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';

	import { exportChatStats } from '$lib/apis/chats';
	import { getVersion } from '$lib/apis';

	import Check from '$lib/components/icons/Check.svelte';

	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let eventData = null;

	let loading = false;
	let completed = false;
	let processedItemsCount = 0;
	let total = 0;

	const syncStats = async () => {
		if (window.opener) {
			window.opener.focus();
			window.opener.postMessage(
				{ type: 'sync:start', requestId: eventData?.requestId ?? null },
				'*'
			);
		}

		const res = await getVersion(localStorage.token).catch(() => {
			return null;
		});
		if (res) {
			window.opener.postMessage(
				{ type: 'sync:version', data: res, requestId: eventData?.requestId ?? null },
				'*'
			);
		}

		loading = true;
		processedItemsCount = 0;
		total = 0;
		let page = 1;

		let allItemsLoaded = false;
		while (!allItemsLoaded) {
			const res = await exportChatStats(
				localStorage.token,
				page,
				eventData?.searchParams ?? {}
			).catch(() => {
				return null;
			});

			if (res) {
				processedItemsCount += res.items.length;
				total = res.total;

				if (window.opener) {
					if (res.items.length > 0) {
						window.opener.postMessage(
							{ type: 'sync:stats:chats', data: res, requestId: eventData?.requestId ?? null },
							'*'
						);
					}
				} else {
					console.log('No opener found to send stats back to.');
				}

				if (processedItemsCount >= total || res.items.length === 0) {
					allItemsLoaded = true;
				} else {
					page += 1;
				}
			} else {
				allItemsLoaded = true;
			}
		}

		// send sync complete message
		if (window.opener) {
			window.opener.postMessage(
				{ type: 'sync:complete', requestId: eventData?.requestId ?? null },
				'*'
			);
		}
		loading = false;
		completed = true;
	};
</script>

<Modal bind:show size="md">
	<div class="w-full">
		{#if completed}
			<div class="flex flex-col items-center justify-center px-6 py-10">
				<Confetti x={[-0.5, 0.5]} y={[0.25, 1]} />

				<div class="rounded-full bg-green-100 dark:bg-green-900/30 p-3 mb-4">
					<Check className="size-8 text-green-600 dark:text-green-400" />
				</div>

				<div class="text-xl font-medium mb-2 text-gray-900 dark:text-gray-100">
					{$i18n.t('Sync Complete!')}
				</div>

				<div class="text-gray-500 dark:text-gray-400 text-center mb-6 max-w-sm text-xs">
					{$i18n.t('Your usage stats have been successfully synced with the Open WebUI Community.')}
				</div>

				<button
					class="px-6 py-1.5 rounded-full text-sm font-medium bg-gray-900 hover:bg-gray-800 text-white dark:bg-white dark:hover:bg-gray-100 dark:text-gray-900 transition-colors"
					on:click={() => (show = false)}
				>
					{$i18n.t('Done')}
				</button>
			</div>
		{:else}
			<div class=" flex justify-between px-5 pt-4 pb-0.5">
				<div class=" text-lg font-medium self-center">{$i18n.t('Sync Usage Stats')}</div>
				<button
					class="self-center"
					on:click={() => {
						show = false;
					}}
					disabled={loading}
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

				{#if loading}
					<div class="mt-3">
						<div class="text-xs text-gray-500 mb-1 flex justify-between">
							<div>{$i18n.t('Syncing stats...')}</div>
							<div>{Math.round((processedItemsCount / total) * 100) || 0}%</div>
						</div>
						<div class="w-full bg-gray-200 rounded-full h-1.5 dark:bg-gray-700">
							<div
								class="bg-gray-900 dark:bg-gray-100 h-1.5 rounded-full transition-all duration-300"
								style="width: {(processedItemsCount / total) * 100}%"
							></div>
						</div>
					</div>
				{/if}

				<div class="mt-5 flex justify-end gap-2">
					<button
						class="px-4 py-2 rounded-full text-sm font-medium bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-900 dark:text-gray-100 transition disabled:cursor-not-allowed"
						on:click={() => (show = false)}
						disabled={loading}
					>
						{$i18n.t('Cancel')}
					</button>
					<button
						class="px-4 py-2 rounded-full text-sm font-medium bg-black hover:bg-gray-900 dark:bg-white dark:hover:bg-gray-100 text-white dark:text-black transition flex items-center gap-2 disabled:cursor-not-allowed"
						on:click={syncStats}
						disabled={loading}
					>
						{$i18n.t('Sync')}

						{#if loading}
							<Spinner className="size-4" />
						{/if}
					</button>
				</div>
			</div>
		{/if}
	</div>
</Modal>
