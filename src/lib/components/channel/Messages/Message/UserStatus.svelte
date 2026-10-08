<script lang="ts">
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	import { user as _user } from '$lib/stores';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { getDMChannelByUserId } from '$lib/apis/channels';

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
	<div class="text-xs">
		<div class="px-3 pt-3 pb-2">
			<div class="flex items-center gap-2">
				<img
					src={`${WEBUI_API_BASE_URL}/users/${user.id}/profile/image`}
					class="size-7 shrink-0 rounded-full object-cover"
					alt=""
				/>
				<div class="min-w-0 flex-1">
					<div
						class="truncate text-[0.8125rem] font-medium leading-5 text-gray-900 dark:text-gray-100"
						title={user.name}
					>
						{user.name}
					</div>
					<div
						class="flex items-center gap-1.5 text-[0.6875rem] leading-4 text-gray-500 dark:text-gray-400"
					>
						<span
							class="size-1.5 shrink-0 rounded-full {user.is_active
								? 'bg-green-500'
								: 'bg-gray-400'}"
							aria-hidden="true"
						></span>
						<span>{user.is_active ? $i18n.t('Active') : $i18n.t('Away')}</span>
					</div>
				</div>
			</div>

			{#if user.status_emoji || user.status_message}
				<div class="mt-2.5">
					<Tooltip content={user.status_message}>
						<div class="flex min-w-0 items-start gap-1.5 text-gray-700 dark:text-gray-300">
							{#if user.status_emoji}
								<div class="flex h-4 shrink-0 items-center">
									<Emoji className="size-3.5" shortCode={user.status_emoji} />
								</div>
							{/if}
							{#if user.status_message}
								<div class="min-w-0 line-clamp-2 text-left leading-4">{user.status_message}</div>
							{/if}
						</div>
					</Tooltip>
				</div>
			{/if}

			{#if user.bio}
				<div class="mt-2">
					<Tooltip content={user.bio}>
						<div class="line-clamp-3 text-left leading-[1.125rem] text-gray-500 dark:text-gray-400">
							{user.bio}
						</div>
					</Tooltip>
				</div>
			{/if}

			{#if (user.groups ?? []).length > 0}
				<div class="mt-2 flex max-h-16 flex-wrap gap-1 overflow-y-auto scrollbar-hover">
					{#each user.groups as group}
						<span
							class="max-w-full break-words rounded-md bg-gray-50 px-1.5 py-0.5 text-[0.6875rem] leading-4 text-gray-600 dark:bg-gray-800/50 dark:text-gray-400"
						>
							{group.name}
						</span>
					{/each}
				</div>
			{/if}
		</div>

		{#if $_user?.id !== user.id}
			<div class="border-t border-gray-50/60 p-1.5 dark:border-gray-800/30">
				<button
					class="flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-left text-xs text-gray-700 transition-colors hover:bg-gray-50/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 dark:text-gray-300 dark:hover:bg-gray-800/60"
					type="button"
					on:click={directMessageHandler}
				>
					<ChatBubbleOval className="size-3.5 shrink-0" />
					<span>{$i18n.t('Message')}</span>
				</button>
			</div>
		{/if}
	</div>
{/if}
