<script lang="ts">
	import { page } from '$app/stores';

	import Chat from '$lib/components/chat/Chat.svelte';
	import { governanceCapabilities, user } from '$lib/stores';
	import { canUsePrivateChat } from '$lib/utils/governance';

	$: privateChatAllowed = canUsePrivateChat($user, $governanceCapabilities);
</script>

{#if privateChatAllowed}
	<Chat chatIdProp={$page.params.id} />
{:else}
	<div class="h-full w-full flex items-center justify-center px-6">
		<div class="max-w-lg text-center space-y-3">
			<h1 class="text-xl font-semibold dark:text-white">
				Private chats are disabled for your role.
			</h1>
			<p class="text-sm text-gray-500 dark:text-gray-400">
				Please use a Team Workspace, or contact admin to assign you to a Team Workspace.
			</p>
		</div>
	</div>
{/if}
