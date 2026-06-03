<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Chat from '$lib/components/chat/Chat.svelte';
	import { page } from '$app/stores';
	import { governanceCapabilities, user, workspaces } from '$lib/stores';
	import { canUsePrivateChat } from '$lib/utils/governance';

	$: privateChatAllowed = canUsePrivateChat($user, $governanceCapabilities);

	onMount(() => {
		if ($page.url.searchParams.get('error')) {
			toast.error($page.url.searchParams.get('error') || 'An unknown error occurred.');
		}
	});
</script>

{#if privateChatAllowed}
	<Chat />
{:else}
	<div class="h-full w-full flex items-center justify-center px-6">
		<div class="max-w-lg text-center space-y-3">
			<h1 class="text-xl font-semibold dark:text-white">Please select a Team Workspace to start a chat.</h1>
			<p class="text-sm text-gray-500 dark:text-gray-400">
				{#if ($workspaces ?? []).length === 0}
					Please contact admin to assign you to a Team Workspace.
				{:else}
					Open a workspace from the sidebar, then use that workspace's New Chat button.
				{/if}
			</p>
		</div>
	</div>
{/if}
