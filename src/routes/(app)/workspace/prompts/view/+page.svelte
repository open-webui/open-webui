<script lang="ts">
	import { toast } from '$lib/utils/toast';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	import { getPromptByCommand } from '$lib/apis/prompts';
	import { page } from '$app/stores';
	import PromptViewer from '$lib/components/workspace/Prompts/PromptViewer.svelte';

	let prompt = null;

	onMount(async () => {
		const command = $page.url.searchParams.get('command');
		if (command) {
			const _prompt = await getPromptByCommand(
				localStorage.token,
				command.replace(/\//g, '')
			).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (_prompt) {
				prompt = {
					title: _prompt.title,
					command: _prompt.command,
					content: _prompt.content,
					access_control: _prompt?.access_control ?? null
				};
			} else {
				goto('/workspace/prompts');
			}
		} else {
			goto('/workspace/prompts');
		}
	});
</script>

{#if prompt}
	<PromptViewer {prompt} />
{/if}
