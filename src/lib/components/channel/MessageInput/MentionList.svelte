<script lang="ts">
	import { getContext, onDestroy, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { channels, models, user } from '$lib/stores';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Hashtag from '$lib/components/icons/Hashtag.svelte';
	import Lock from '$lib/components/icons/Lock.svelte';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { searchUsers } from '$lib/apis/users';

	export let query = '';

	export let command: (payload: { id: string; label: string }) => void;
	export let selectedIndex = 0;

	export let label = '';
	export let triggerChar = '@';

	export let modelSuggestions = false;
	export let userSuggestions = false;
	export let channelSuggestions = false;

	let _models = [];
	let _users = [];
	let _channels = [];

	$: filteredItems = [..._users, ..._models, ..._channels].filter(
		(u) =>
			u.label.toLowerCase().includes(query.toLowerCase()) ||
			u.id.toLowerCase().includes(query.toLowerCase())
	);

	const getUserList = async () => {
		const res = await searchUsers(localStorage.token, query).catch((error) => {
			console.error('Error searching users:', error);
			return null;
		});

		if (res) {
			_users = [...res.users.map((u) => ({ type: 'user', id: u.id, label: u.name }))].sort((a, b) =>
				a.label.localeCompare(b.label)
			);
		}
	};

	$: if (query !== null && userSuggestions) {
		getUserList();
	}

	const select = (index: number) => {
		const item = filteredItems[index];
		if (!item) return;

		// Add the "U:", "M:" or "C:" prefix to the id
		// and also append the label after a pipe |
		// so that the mention renderer can show the label
		if (item)
			command({
				id: `${item.type === 'user' ? 'U' : item.type === 'model' ? 'M' : 'C'}:${item.id}|${item.label}`,
				label: item.label
			});
	};

	const onKeyDown = (event: KeyboardEvent) => {
		if (!['ArrowUp', 'ArrowDown', 'Enter', 'Tab', 'Escape'].includes(event.key)) return false;

		if (event.key === 'ArrowUp') {
			selectedIndex = Math.max(0, selectedIndex - 1);
			const item = document.querySelector(`[data-selected="true"]`);
			item?.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
			return true;
		}
		if (event.key === 'ArrowDown') {
			selectedIndex = Math.min(selectedIndex + 1, filteredItems.length - 1);
			const item = document.querySelector(`[data-selected="true"]`);
			item?.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
			return true;
		}
		if (event.key === 'Enter' || event.key === 'Tab') {
			select(selectedIndex);

			if (event.key === 'Enter') {
				event.preventDefault();
			}
			return true;
		}
		if (event.key === 'Escape') {
			// tell tiptap we handled it (it will close)
			return true;
		}
		return false;
	};

	// This method will be called from the suggestion renderer
	// @ts-ignore
	export function _onKeyDown(event: KeyboardEvent) {
		return onKeyDown(event);
	}

	const keydownListener = (e) => {
		// required to prevent the default enter behavior
		if (e.key === 'Enter') {
			e.preventDefault();
			select(selectedIndex);
		}
	};

	onMount(async () => {
		window.addEventListener('keydown', keydownListener);
		if (channelSuggestions) {
			// Add a dummy channel item
			_channels = [
				...$channels
					.filter((c) => c?.type !== 'dm')
					.map((c) => ({ type: 'channel', id: c.id, label: c.name, data: c }))
			];
		} else {
			if (userSuggestions) {
				await getUserList();
			}

			if (modelSuggestions) {
				_models = [...$models.map((m) => ({ type: 'model', id: m.id, label: m.name, data: m }))];
			}
		}
	});

	onDestroy(() => {
		window.removeEventListener('keydown', keydownListener);
	});
</script>

{#if filteredItems.length}
	<div
		class="mention-list text-black dark:text-white rounded-2xl shadow-lg border border-gray-200 dark:border-gray-800 flex flex-col bg-white dark:bg-gray-850 w-72 p-1"
		id="suggestions-container"
	>
		<div class="overflow-y-auto scrollbar-thin max-h-60">
			{#each filteredItems as item, i}
				{#if i === 0 || item?.type !== filteredItems[i - 1]?.type}
					<div class="px-2 text-xs text-gray-500 py-1">
						{#if item?.type === 'user'}
							{$i18n.t('Users')}
						{:else if item?.type === 'model'}
							{$i18n.t('Models')}
						{:else if item?.type === 'channel'}
							{$i18n.t('Channels')}
						{/if}
					</div>
				{/if}

				<Tooltip content={item?.id} placement="top-start">
					<button
						type="button"
						on:click={() => select(i)}
						on:mousemove={() => {
							selectedIndex = i;
						}}
						class="flex items-center justify-between px-2.5 py-1.5 rounded-xl w-full text-left {i ===
						selectedIndex
							? 'bg-gray-50 dark:bg-gray-800 selected-command-option-button'
							: ''}"
						data-selected={i === selectedIndex}
					>
						{#if item.type === 'channel'}
							<div class=" size-4 justify-center flex items-center mr-0.5">
								{#if item?.data?.access_control === null}
									<Hashtag className="size-3" strokeWidth="2.5" />
								{:else}
									<Lock className="size-[15px]" strokeWidth="2" />
								{/if}
							</div>
						{:else if item.type === 'model'}
							<img
								src={`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${item.id}&lang=${$i18n.language}`}
								alt={item?.data?.name ?? item.id}
								class="rounded-full size-5 items-center mr-2"
							/>
						{:else if item.type === 'user'}
							<img
								src={`${WEBUI_API_BASE_URL}/users/${item.id}/profile/image`}
								alt={item?.label ?? item.id}
								class="rounded-full size-5 items-center mr-2"
							/>
						{/if}

						<div class="truncate flex-1 pr-2">
							{item.label}
						</div>

						<div class="shrink-0 text-xs text-gray-500">
							{#if item.type === 'user'}
								{$i18n.t('User')}
							{:else if item.type === 'model'}
								{$i18n.t('Model')}
							{:else if item.type === 'channel'}
								{$i18n.t('Channel')}
							{/if}
						</div>
					</button>
				</Tooltip>
			{/each}
		</div>
	</div>
{/if}
