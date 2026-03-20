<script lang="ts">
	import { getContext, onMount } from 'svelte';

	const i18n = getContext('i18n');

	import { user as _user, channels, socket } from '$lib/stores';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { getChannels, getDMChannelByUserId } from '$lib/apis/channels';

	import ChatBubbles from '$lib/components/icons/ChatBubbles.svelte';
	import ChatBubble from '$lib/components/icons/ChatBubble.svelte';
	import ChatBubbleOval from '$lib/components/icons/ChatBubbleOval.svelte';
	import { goto } from '$app/navigation';
	import Emoji from '$lib/components/common/Emoji.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	export let user = null;

	const directMessageHandler = async () => {
		if (!user) {
			return;
		}

		const res = await getDMChannelByUserId(localStorage.token, user.id).catch((error) => {
			console.error('Error fetching DM channel:', error);
			return null;
		});

		if (res) {
			goto(`/channels/${res.id}`);
		}
	};
</script>

{#if user}
	<div class="py-3">
		<div class=" flex gap-3.5 w-full px-3 items-center">
			<div class=" items-center flex shrink-0">
				<img
					src={`${WEBUI_API_BASE_URL}/users/${user?.id}/profile/image`}
					class=" size-14 object-cover rounded-xl"
					alt="profile"
				/>
			</div>

			<div class=" flex flex-col w-full flex-1">
				<div class="mb-0.5 font-medium line-clamp-1 pr-2">
					{user.name}
				</div>

				<div class=" flex items-center gap-2">
					{#if user?.is_active}
						<div>
							<span class="relative flex size-2">
								<span
									class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"
								/>
								<span class="relative inline-flex rounded-full size-2 bg-green-500" />
							</span>
						</div>

						<span class="text-xs"> {$i18n.t('Active')} </span>
					{:else}
						<div>
							<span class="relative flex size-2">
								<span class="relative inline-flex rounded-full size-2 bg-gray-500" />
							</span>
						</div>

						<span class="text-xs"> {$i18n.t('Away')} </span>
					{/if}
				</div>
			</div>
		</div>

		{#if user?.status_emoji || user?.status_message}
			<div class="mx-2 mt-2">
				<Tooltip content={user?.status_message}>
					<div
						class="w-full gap-2 px-2.5 py-1.5 rounded-xl bg-gray-50 dark:text-white dark:bg-gray-900/50 text-black transition text-xs flex items-center"
					>
						{#if user?.status_emoji}
							<div class=" self-center shrink-0">
								<Emoji className="size-4" shortCode={user?.status_emoji} />
							</div>
						{/if}
						<div class=" self-center line-clamp-2 flex-1 text-left">
							{user?.status_message}
						</div>
					</div>
				</Tooltip>
			</div>
		{/if}

		{#if user?.bio}
			<div class="mx-3.5 mt-2">
				<Tooltip content={user?.bio}>
					<div class=" self-center line-clamp-3 flex-1 text-left text-xs">
						{user?.bio}
					</div>
				</Tooltip>
			</div>
		{/if}

		{#if (user?.groups ?? []).length > 0}
			<div class="mx-3.5 mt-2 flex gap-0.5">
				{#each user.groups as group}
					<div
						class="px-1.5 py-0.5 rounded-lg bg-gray-50 dark:text-white dark:bg-gray-900/50 text-black transition text-xs"
					>
						{group.name}
					</div>
				{/each}
			</div>
		{/if}

		{#if $_user?.id !== user.id}
			<hr class="border-gray-100/50 dark:border-gray-800/50 my-2.5" />

			<div class=" flex flex-col w-full px-2.5 items-center">
				<button
					class="w-full text-left px-3 py-1.5 rounded-xl border border-gray-100/50 dark:border-gray-800/50 hover:bg-gray-50 dark:hover:bg-gray-850 transition flex items-center gap-2 text-sm"
					type="button"
					on:click={() => {
						directMessageHandler();
					}}
				>
					<div>
						<ChatBubbleOval className="size-4" />
					</div>

					<div class="font-medium">
						{$i18n.t('Message')}
					</div>
				</button>
			</div>
		{/if}
	</div>
{/if}
