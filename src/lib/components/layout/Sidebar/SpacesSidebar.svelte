<script lang="ts">
	import { onMount, getContext, tick } from 'svelte';
	const i18n = getContext('i18n');

	import { goto } from '$app/navigation';
	import { mobile, showSidebar, user } from '$lib/stores';
	import {
		getSpaces,
		getPendingInvitations,
		getBookmarkedSpaces,
		getPinnedSpaces,
		type Space,
		type InvitationWithSpace
	} from '$lib/apis/spaces';

	import Folder from '$lib/components/common/Folder.svelte';
	import SpaceItem from './SpaceItem.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	export let onCreateSpace: () => void = () => {};

	let privateSpaces: Space[] = [];
	let sharedSpaces: Space[] = [];
	let invitedSpaces: InvitationWithSpace[] = [];
	let bookmarkedSpaces: Space[] = [];
	let pinnedSpaces: Space[] = [];
	let loading = true;
	let showSpaces = false;

	const loadSpaces = async () => {
		loading = true;
		try {
			const [privateRes, sharedRes, invites, bookmarks, pinned] = await Promise.all([
				getSpaces(localStorage.token, null, 'private'),
				getSpaces(localStorage.token, null, 'shared'),
				getPendingInvitations(localStorage.token),
				getBookmarkedSpaces(localStorage.token).catch(() => []),
				getPinnedSpaces(localStorage.token).catch(() => [])
			]);
			privateSpaces = privateRes?.items ?? [];
			sharedSpaces = sharedRes?.items ?? [];
			invitedSpaces = invites ?? [];
			bookmarkedSpaces = bookmarks ?? [];
			pinnedSpaces = pinned ?? [];
		} catch (error) {
			console.error('Failed to load spaces:', error);
			privateSpaces = [];
			sharedSpaces = [];
			invitedSpaces = [];
			bookmarkedSpaces = [];
			pinnedSpaces = [];
		}
		loading = false;
	};

	onMount(async () => {
		await loadSpaces();
	});

	export const refresh = async () => {
		await loadSpaces();
	};

	$: hasAnySpaces =
		privateSpaces.length > 0 ||
		sharedSpaces.length > 0 ||
		invitedSpaces.length > 0 ||
		bookmarkedSpaces.length > 0 ||
		pinnedSpaces.length > 0;
</script>

<Folder
	id="sidebar-spaces"
	bind:open={showSpaces}
	className="px-2 mt-0.5"
	name={$i18n.t('Spaces')}
	badge={invitedSpaces.length}
	chevron={false}
	dragAndDrop={false}
	onAdd={() => {
		onCreateSpace();
	}}
	onAddLabel={$i18n.t('New Space')}
>
	<svelte:fragment slot="icon">
		<svg
			xmlns="http://www.w3.org/2000/svg"
			fill="none"
			viewBox="0 0 24 24"
			stroke-width="2"
			stroke="currentColor"
			class="size-4"
		>
			<path
				stroke-linecap="round"
				stroke-linejoin="round"
				d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.25 0 0 1 13.5 18v-2.25Z"
			/>
		</svg>
	</svelte:fragment>
	{#if loading}
		<div class="flex justify-center py-2">
			<Spinner className="size-4" />
		</div>
	{:else if !hasAnySpaces}
		<div class="px-2 py-2 text-xs text-gray-500 dark:text-gray-500">
			{$i18n.t('No spaces yet. Create one to get started!')}
		</div>
	{:else}
		<div
			class="ml-3 pl-1 mt-[1px] flex flex-col overflow-y-auto scrollbar-hidden border-s border-gray-100 dark:border-gray-900"
		>
			{#if pinnedSpaces.length > 0}
				<div
					class="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-accent-500 dark:text-accent-400"
				>
					{$i18n.t('Pinned')}
				</div>
				{#each pinnedSpaces as space (space.id)}
					<SpaceItem {space} />
				{/each}
			{/if}

			{#if bookmarkedSpaces.length > 0}
				<div
					class="px-2 py-1 {pinnedSpaces.length > 0
						? 'mt-1'
						: ''} text-[10px] font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-400"
				>
					{$i18n.t('Bookmarked')}
				</div>
				{#each bookmarkedSpaces as space (space.id)}
					<SpaceItem {space} />
				{/each}
			{/if}

			{#if invitedSpaces.length > 0}
				<div
					class="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-400"
				>
					{$i18n.t('Invitations')}
				</div>
				{#each invitedSpaces as invite (invite.id)}
					<button
						class="w-full text-left px-2 py-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-900 transition text-sm truncate flex items-center gap-1.5"
						on:click={() => goto(`/spaces/${invite.space_slug}`)}
					>
						{#if invite.space_emoji}
							<span class="text-xs">{invite.space_emoji}</span>
						{/if}
						<span class="truncate text-gray-700 dark:text-gray-300">{invite.space_name}</span>
						<span class="ml-auto flex-shrink-0 w-1.5 h-1.5 rounded-full bg-amber-500"></span>
					</button>
				{/each}
			{/if}

			{#if privateSpaces.length > 0}
				{#if sharedSpaces.length > 0 || invitedSpaces.length > 0}
					<div
						class="px-2 py-1 mt-1 text-[10px] font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-600"
					>
						{$i18n.t('My Spaces')}
					</div>
				{/if}
				{#each privateSpaces as space (space.id)}
					<SpaceItem {space} />
				{/each}
			{/if}

			{#if sharedSpaces.length > 0}
				<div
					class="px-2 py-1 mt-1 text-[10px] font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-600"
				>
					{$i18n.t('Shared')}
				</div>
				{#each sharedSpaces as space (space.id)}
					<SpaceItem {space} />
				{/each}
			{/if}

			<button
				class="w-full text-left px-2 py-1.5 mt-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-900 transition text-xs text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300"
				on:click={() => goto('/spaces')}
			>
				{$i18n.t('View all spaces')}
			</button>
		</div>
	{/if}
</Folder>
