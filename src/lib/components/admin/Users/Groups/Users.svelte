<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { WEBUI_BASE_URL } from '$lib/constants';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Badge from '$lib/components/common/Badge.svelte';

	export let users = [];
	export let userIds = [];

	let filteredUsers = [];

	$: filteredUsers = users
		.filter((user) => {
			if (user?.role === 'admin') {
				return false;
			}

			if (query === '') {
				return true;
			}

			return (
				user.name.toLowerCase().includes(query.toLowerCase()) ||
				user.email.toLowerCase().includes(query.toLowerCase())
			);
		})
		.sort((a, b) => {
			const aUserIndex = userIds.indexOf(a.id);
			const bUserIndex = userIds.indexOf(b.id);

			// Compare based on userIds or fall back to alphabetical order
			if (aUserIndex !== -1 && bUserIndex === -1) return -1; // 'a' has valid userId -> prioritize
			if (bUserIndex !== -1 && aUserIndex === -1) return 1; // 'b' has valid userId -> prioritize

			// Both a and b are either in the userIds array or not, so we'll sort them by their indices
			if (aUserIndex !== -1 && bUserIndex !== -1) return aUserIndex - bUserIndex;

			// If both are not in the userIds, fallback to alphabetical sorting by name
			return a.name.localeCompare(b.name);
		});

	$: selectedCount = userIds.length;

	let query = '';
</script>

<div class="space-y-3">
	<div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white/70 dark:bg-gray-900/40 px-3 py-2.5">
		<div class="flex w-full items-center gap-2.5">
			<div class="self-center text-gray-400 dark:text-gray-500">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-4 h-4"
				>
					<path
						fill-rule="evenodd"
						d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
						clip-rule="evenodd"
					/>
				</svg>
			</div>
			<input
				class="w-full text-sm pr-2 outline-none bg-transparent text-gray-800 dark:text-gray-100 placeholder:text-gray-400 dark:placeholder:text-gray-500"
				bind:value={query}
				placeholder={$i18n.t('Search')}
			/>
			{#if selectedCount > 0}
				<div class="text-xs font-medium text-blue-600 dark:text-blue-400 whitespace-nowrap">
					{selectedCount} selected
				</div>
			{/if}
		</div>
	</div>

	<div class="max-h-[22rem] overflow-y-auto scrollbar-hidden pr-0.5">
		<div class="flex flex-col gap-1.5">
			{#if filteredUsers.length > 0}
				{#each filteredUsers as user, userIdx (user.id)}
					<div
						class="flex flex-row items-center gap-3 w-full text-sm rounded-xl border px-3 py-2.5 transition-colors {userIds.includes(
							user.id
						)
							? 'border-blue-200 bg-blue-50/60 dark:border-blue-800/60 dark:bg-blue-900/20'
							: 'border-gray-200 dark:border-gray-700 bg-white/80 dark:bg-gray-900/40 hover:bg-gray-50 dark:hover:bg-gray-800/60'}"
					>
						<div class="flex items-center pt-0.5">
							<Checkbox
								state={userIds.includes(user.id) ? 'checked' : 'unchecked'}
								on:change={(e) => {
									if (e.detail === 'checked') {
										userIds = [...userIds, user.id];
									} else {
										userIds = userIds.filter((id) => id !== user.id);
									}
								}}
							/>
						</div>

						<div class="flex w-full items-center justify-between">
							<div class="flex min-w-0 items-center">
								<img
									class="rounded-full size-7 object-cover mr-2.5 border border-gray-200 dark:border-gray-700"
									src={user.profile_image_url.startsWith(WEBUI_BASE_URL) ||
									user.profile_image_url.startsWith('https://www.gravatar.com/avatar/') ||
									user.profile_image_url.startsWith('data:')
										? user.profile_image_url
										: `/user.png`}
									alt="user"
								/>

								<div class="min-w-0">
									<div class="font-medium text-gray-800 dark:text-gray-100 truncate">{user.name}</div>
									<div class="text-xs text-gray-500 dark:text-gray-400 truncate">{user.email}</div>
								</div>
							</div>

							{#if userIds.includes(user.id)}
								<Badge type="success" content="member" />
							{/if}
						</div>
					</div>
				{/each}
			{:else}
				<div class="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 py-8 px-6 text-center bg-white/50 dark:bg-gray-900/30">
					<div class="text-sm font-medium text-gray-600 dark:text-gray-300">{$i18n.t('No users were found.')}</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-1">Try searching with a different name or email.</div>
				</div>
			{/if}
		</div>
	</div>
</div>
