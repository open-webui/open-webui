<script>
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { prompts } from '$lib/stores';
	import { onMount, tick, getContext } from 'svelte';

	import { getPrompts, updatePromptByCommand } from '$lib/apis/prompts';
	import { page } from '$app/stores';

	import PromptEditor from '$lib/components/workspace/Prompts/PromptEditor.svelte';

	let prompt = null;
	const onSubmit = async ({ title, command, content }) => {
		const prompt = await updatePromptByCommand(localStorage.token, command, title, content).catch(
			(error) => {
				toast.error(error);
				return null;
			}
		);

		if (prompt) {
			await prompts.set(await getPrompts(localStorage.token));
			await goto('/workspace/prompts');
		}
	};

	onMount(async () => {
		const command = $page.url.searchParams.get('command');
		if (command) {
			const _prompt = $prompts.filter((prompt) => prompt.command === command).at(0);

			if (_prompt) {
				prompt = {
					title: _prompt.title,
					command: _prompt.command,
					content: _prompt.content
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
	<PromptEditor {prompt} {onSubmit} edit />
{/if}
