<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
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

	let query = '';
</script>

<div>
	<div class="flex w-full">
		<div class="flex flex-1">
			<div class=" self-center mr-3">
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
				class=" w-full text-sm pr-4 rounded-r-xl outline-hidden bg-transparent"
				bind:value={query}
				placeholder={$i18n.t('Search')}
			/>
		</div>
	</div>

	<div class="mt-3 max-h-[22rem] overflow-y-auto scrollbar-hidden">
		<div class="flex flex-col gap-2.5">
			{#if filteredUsers.length > 0}
				{#each filteredUsers as user, userIdx (user.id)}
					<div class="flex flex-row items-center gap-3 w-full text-sm">
						<div class="flex items-center">
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
							<Tooltip content={user.email} placement="top-start">
								<div class="flex">
									<img
										class=" rounded-full size-5 object-cover mr-2.5"
										src={user.profile_image_url.startsWith(WEBUI_BASE_URL) ||
										user.profile_image_url.startsWith('https://www.gravatar.com/avatar/') ||
										user.profile_image_url.startsWith('data:')
											? user.profile_image_url
											: `/user.png`}
										alt="user"
									/>

									<div class=" font-medium self-center">{user.name}</div>
								</div>
							</Tooltip>

							{#if userIds.includes(user.id)}
								<Badge type="success" content="member" />
							{/if}
						</div>
					</div>
				{/each}
			{:else}
				<div class="text-gray-500 text-xs text-center py-2 px-10">
					{$i18n.t('No users were found.')}
				</div>
			{/if}
		</div>
	</div>
</div>
