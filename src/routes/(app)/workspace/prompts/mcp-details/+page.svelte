<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { getMCPPrompts } from '$lib/apis/mcp-prompts';
	import { user } from '$lib/stores';
	import McpPromptDetails from '$lib/components/workspace/Prompts/McpPromptDetails.svelte';

	let selectedPrompt = null;

	onMount(async () => {
		const serverId = $page.url.searchParams.get('server_id');
		const name = $page.url.searchParams.get('name');

		if (serverId && name) {
			const mcpPrompts = await getMCPPrompts($user.token);
			selectedPrompt = mcpPrompts.find((p) => p.server_id === serverId && p.name === name) || null;

			if (!selectedPrompt) {
				goto('/workspace/prompts');
			}
		} else {
			goto('/workspace/prompts');
		}
	});
</script>

{#if selectedPrompt}
	<div class="w-full max-h-full flex justify-center">
		<div class="flex flex-col w-full mb-10">
			<div class="mb-4">
				<a
					class="text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition"
					href="/workspace/prompts"
				>
					← Back to prompts
				</a>
			</div>
			<McpPromptDetails prompt={selectedPrompt} />
		</div>
	</div>
{/if}
