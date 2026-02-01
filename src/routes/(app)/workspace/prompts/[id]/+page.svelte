<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { prompts } from '$lib/stores';
	import { onMount, getContext } from 'svelte';

	const i18n = getContext('i18n');

	import { getPromptById, getPrompts, updatePromptById } from '$lib/apis/prompts';
	import { page } from '$app/stores';

	import PromptEditor from '$lib/components/workspace/Prompts/PromptEditor.svelte';

	let prompt = null;
	let disabled = false;

	// Get prompt ID from route params
	$: promptId = $page.params.id;

	const onSubmit = async (_prompt) => {
		console.log(_prompt);
		const updatedPrompt = await updatePromptById(localStorage.token, _prompt).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (updatedPrompt) {
			toast.success($i18n.t('Prompt updated successfully'));
			await prompts.set(await getPrompts(localStorage.token));
			// Update local prompt state to reflect the new version
			prompt = {
				id: updatedPrompt.id,
				name: updatedPrompt.name,
				command: updatedPrompt.command,
				content: updatedPrompt.content,
				version_id: updatedPrompt.version_id,
				tags: updatedPrompt.tags,
				access_control: updatedPrompt?.access_control === undefined ? {} : updatedPrompt?.access_control
			};
		}
	};

	onMount(async () => {
		if (promptId) {
			const _prompt = await getPromptById(
				localStorage.token,
				promptId
			).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (_prompt) {
				disabled = !_prompt.write_access ?? true;
				prompt = {
					id: _prompt.id,
					name: _prompt.name,
					command: _prompt.command,
					content: _prompt.content,
					version_id: _prompt.version_id,
					tags: _prompt.tags,
					access_control: _prompt?.access_control === undefined ? {} : _prompt?.access_control
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
	<PromptEditor {prompt} {onSubmit} {disabled} edit />
{/if}
