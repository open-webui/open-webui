<script lang="ts">
	import ProfileImage from '$lib/components/chat/Messages/ProfileImage.svelte';
	import { getAbortSignal, getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { getChannelMentionApps } from '$lib/apis/channels';
	import { mentionAttributes } from '$lib/utils/channelMentions';
	import { channels, models, config } from '$lib/stores';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Grid from '$lib/components/icons/Grid.svelte';
	import Hashtag from '$lib/components/icons/Hashtag.svelte';
	import Lock from '$lib/components/icons/Lock.svelte';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { searchUsers } from '$lib/apis/users';
	import { getChannelMembersById } from '$lib/apis/channels';

	export let query = '';

	export let command: (payload: { id: string; label: string }) => void;
	export let selectedIndex = 0;

	export let label = '';
	export let triggerChar = '@';

	export let modelSuggestions = false;
	export let userSuggestions = false;
	export let channelSuggestions = false;
	export let channelId: string | null = null;
	export let loadUsers:
		| ((query: string, signal: AbortSignal) => Promise<{ id: string; name: string }[]>)
		| null = null;

	let _models = [];
	let _users = [];
	let _channels = [];
	let _apps: { type: string; id: string; label: string; profile_image_url?: string | null }[] = [];

	type UserSuggestion = { id: string; name: string };

	$: filteredItems = [..._users, ..._models, ..._channels, ..._apps].filter(
		(u) =>
			u.label.toLowerCase().includes(query.toLowerCase()) ||
			u.id.toLowerCase().includes(query.toLowerCase())
	);

	const toUserItems = (users: UserSuggestion[]) =>
		[...users]
			.map((u) => ({ type: 'user', id: u.id, label: u.name }))
			.sort((a, b) => a.label.localeCompare(b.label));

	const getUserList = async (requestQuery: string, requestChannelId: string | null) => {
		const signal = getAbortSignal();
		if (loadUsers) {
			const users = await loadUsers(requestQuery, signal).catch(() => []);
			if (!signal.aborted) _users = toUserItems(users);
			return;
		}
		const [channelMembers, searchResults] = await Promise.all([
			requestChannelId
				? getChannelMembersById(
						localStorage.token,
						requestChannelId,
						requestQuery,
						'name',
						'asc',
						1,
						signal
					).catch((error) => {
						if (signal.aborted) return null;
						console.error('Error loading channel members:', error);
						return null;
					})
				: Promise.resolve(null),
			searchUsers(localStorage.token, requestQuery, undefined, undefined, 1, signal).catch(
				(error) => {
					if (signal.aborted) return null;
					console.error('Error searching users:', error);
					return null;
				}
			)
		]);

		if (signal.aborted) return;

		const memberUsers = (channelMembers?.users ?? []) as UserSuggestion[];
		const searchedUsers = (searchResults?.users ?? []) as UserSuggestion[];
		const memberIds = new Set(memberUsers.map((u) => u.id));
		const globalUsers = searchedUsers.filter((u) => !memberIds.has(u.id));

		_users = [...toUserItems(memberUsers), ...toUserItems(globalUsers)];
	};

	$: if (query !== null && userSuggestions) {
		getUserList(query, channelId);
	}

	const select = (index: number) => {
		const item = filteredItems[index];
		if (!item) return;

		command(mentionAttributes(item));
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

	onMount(() => {
		if ($config?.features?.enable_apps && channelId && triggerChar === '@') {
			getChannelMentionApps(localStorage.token, channelId)
				.then((apps) => {
					_apps = apps.map((a) => ({
						type: 'app',
						id: a.id,
						label: a.name,
						profile_image_url: a.data.manifest.profile_image_url
					}));
				})
				.catch(() => {});
		}
		const keydownListener = (e: KeyboardEvent) => {
			// required to prevent the default enter behavior
			if (e.key === 'Enter') {
				e.preventDefault();
				select(selectedIndex);
			}
		};

		window.addEventListener('keydown', keydownListener);

		if (channelSuggestions) {
			// Add a dummy channel item
			_channels = [
				...$channels
					.filter((c) => c?.type !== 'dm')
					.map((c) => ({ type: 'channel', id: c.id, label: c.name, data: c }))
			];
		} else {
			if (modelSuggestions) {
				_models = [
					...$models
						.filter((m) => !m?.direct)
						.map((m) => ({ type: 'model', id: m.id, label: m.name, data: m }))
				];
			}
		}

		return () => {
			window.removeEventListener('keydown', keydownListener);
		};
	});

	const hasPublicReadGrant = (grants: any) =>
		Array.isArray(grants) &&
		grants.some(
			(grant) =>
				grant?.principal_type === 'user' &&
				grant?.principal_id === '*' &&
				grant?.permission === 'read'
		);

	const isPublicChannel = (channel: any): boolean => {
		if (channel?.type === 'group') {
			if (typeof channel?.is_private === 'boolean') {
				return !channel.is_private;
			}
			return hasPublicReadGrant(channel?.access_grants);
		}
		return hasPublicReadGrant(channel?.access_grants);
	};
</script>

{#if filteredItems.length}
	<div class="mention-list" id="suggestions-container">
		<DropdownMenu className="w-72 max-w-[calc(100vw-1rem)] overflow-x-hidden font-sans text-xs">
			<div class="overflow-y-auto overflow-x-hidden scrollbar-thin max-h-60">
				{#each filteredItems as item, i}
					{#if i === 0 || item?.type !== filteredItems[i - 1]?.type}
						<div class="app-muted mb-0.5 px-2 pt-1 pb-0.5 text-[0.625rem] leading-none">
							{#if item?.type === 'user'}
								{$i18n.t('Users')}
							{:else if item?.type === 'model'}
								{$i18n.t('Models')}
							{:else if item?.type === 'app'}
								{$i18n.t('Apps')}
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
							class="flex h-6 w-full items-center gap-2 rounded-xl px-2 text-left text-xs transition-colors duration-75 hover:bg-gray-50/40 dark:hover:bg-gray-800/40 {i ===
							selectedIndex
								? 'app-interactive-active selected-command-option-button'
								: ''}"
							data-selected={i === selectedIndex}
						>
							{#if item.type === 'channel'}
								<div class="app-icon-muted flex w-4 shrink-0 items-center justify-center">
									{#if isPublicChannel(item?.data)}
										<Hashtag className="size-3.5" strokeWidth="1.6" />
									{:else}
										<Lock className="size-3.5" strokeWidth="1.6" />
									{/if}
								</div>
							{:else if item.type === 'app'}
								{#if item.profile_image_url}
									<ProfileImage
										src={item.profile_image_url}
										allowExternal
										className="size-4 shrink-0 rounded-sm!"
									/>
								{:else}<Grid className="app-icon-muted size-4 shrink-0" />{/if}
							{:else if item.type === 'model'}
								<img
									src={`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${item.id}&lang=${$i18n.language}`}
									alt={item?.data?.name ?? item.id}
									class="size-4 shrink-0 rounded-full object-cover"
									on:error={(e) => {
										// LICENSE covers this Open WebUI fallback logo.
										// Do not alter, remove, obscure, or replace it except as LICENSE permits:
										// https://docs.openwebui.com/license.
										e.currentTarget.src = '/favicon.png';
									}}
								/>
							{:else if item.type === 'user'}
								<img
									src={`${WEBUI_API_BASE_URL}/users/${item.id}/profile/image`}
									alt={item?.label ?? item.id}
									class="size-4 shrink-0 rounded-full object-cover"
									on:error={(e) => {
										// LICENSE covers this Open WebUI fallback logo.
										// Do not alter, remove, obscure, or replace it except as LICENSE permits:
										// https://docs.openwebui.com/license.
										e.currentTarget.src = '/favicon.png';
									}}
								/>
							{/if}

							<div class="min-w-0 flex-1 truncate">
								{item.label}
							</div>

							<div class="app-muted max-w-24 shrink-0 truncate text-[0.625rem]">
								{#if item.type === 'user'}
									{$i18n.t('User')}
								{:else if item.type === 'model'}
									{$i18n.t('Model')}
								{:else if item.type === 'app'}
									{$i18n.t('App')}
								{:else if item.type === 'channel'}
									{$i18n.t('Channel')}
								{/if}
							</div>
						</button>
					</Tooltip>
				{/each}
			</div>
		</DropdownMenu>
	</div>
{/if}
