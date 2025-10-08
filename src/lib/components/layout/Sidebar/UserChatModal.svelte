<script lang="ts">
	import { createEventDispatcher, getContext, onDestroy } from 'svelte';
	import { toast } from 'svelte-sonner';

import Modal from '$lib/components/common/Modal.svelte';
import Spinner from '$lib/components/common/Spinner.svelte';
import Search from '$lib/components/icons/Search.svelte';

import { getChatPeers } from '$lib/apis/users';
import { WEBUI_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let busy = false;

	let loading = false;
	let peers: Array<{ id: string; name: string; role?: string; profile_image_url?: string }> = [];
	let searchTerm = '';
	let initialized = false;
	let searchTimeout: ReturnType<typeof setTimeout> | null = null;

	const loadPeers = async () => {
		loading = true;

		const res = await getChatPeers(localStorage.token, searchTerm).catch((error) => {
			toast.error(`${error}`);
			return [];
		});

		peers = res ?? [];
		loading = false;
	};

	$: if (show && !initialized) {
		initialized = true;
		loadPeers();
	}

	$: if (!show && initialized) {
		initialized = false;
		searchTerm = '';
		peers = [];
		if (searchTimeout) {
			clearTimeout(searchTimeout);
			searchTimeout = null;
		}
	}

	const handleSearchInput = (event: Event) => {
		const target = event.target as HTMLInputElement;
		searchTerm = target.value;

		if (searchTimeout) {
			clearTimeout(searchTimeout);
		}

		searchTimeout = setTimeout(() => {
			loadPeers();
		}, 250);
	};

	const handleSelect = (peer) => {
		if (busy) {
			return;
		}
		dispatch('select', { peer });
	};

	onDestroy(() => {
		if (searchTimeout) {
			clearTimeout(searchTimeout);
		}
	});
</script>

<Modal size="md" bind:show>
	<div class="flex flex-col gap-4 px-5 pt-4 pb-5 text-gray-900 dark:text-gray-100">
		<header class="flex items-center justify-between">
			<h2 class="text-lg font-semibold">
				{$i18n.t('Chat with users')}
			</h2>
		</header>

		<div class="relative">
			<div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-gray-400">
				<Search className="size-4" />
			</div>
			<input
				class="w-full rounded-lg border border-gray-200 bg-white py-2 pl-9 pr-3 text-sm outline-none focus:border-gray-400 dark:border-gray-800 dark:bg-gray-950 dark:text-gray-100"
				type="text"
				name="search-user"
				placeholder={$i18n.t('Search users')}
				autocomplete="off"
				on:input={handleSearchInput}
			/>
		</div>

		{#if loading}
			<div class="flex justify-center py-8">
				<Spinner />
			</div>
		{:else if peers.length === 0}
			<div class="rounded-lg border border-dashed border-gray-200 bg-gray-50 px-4 py-6 text-center text-sm text-gray-500 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-400">
				{$i18n.t('No users found. Try a different search.')}
			</div>
		{:else}
			<ul class="flex max-h-72 flex-col gap-2 overflow-y-auto pr-1">
				{#each peers as peer}
					<li>
						<button
							class="flex w-full items-center gap-3 rounded-lg border border-transparent bg-gray-100 px-3 py-2 text-left text-sm transition hover:border-gray-200 hover:bg-gray-200 focus:outline-none disabled:cursor-not-allowed disabled:opacity-75 dark:bg-gray-900 dark:hover:bg-gray-850"
							on:click={() => handleSelect(peer)}
							disabled={busy}
						>
							<img
								src={peer.profile_image_url ?? `${WEBUI_BASE_URL}/static/favicon.png`}
								alt={peer.name}
								class="size-8 rounded-full object-cover"
								loading="lazy"
							/>
							<div class="flex flex-col">
								<span class="font-medium text-gray-900 dark:text-gray-100">{peer.name}</span>
								{#if peer.role}
									<span class="text-xs text-gray-500 dark:text-gray-400">
										{$i18n.t(peer.role)}
									</span>
								{/if}
							</div>
						</button>
					</li>
				{/each}
			</ul>
		{/if}
	</div>
</Modal>
