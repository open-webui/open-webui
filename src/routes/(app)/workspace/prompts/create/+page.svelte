<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { prompts } from '$lib/stores';
	import { onMount, tick, getContext } from 'svelte';

	const i18n = getContext('i18n');

	import { createNewPrompt, getPrompts } from '$lib/apis/prompts';
	import PromptEditor from '$lib/components/workspace/Prompts/PromptEditor.svelte';

	let prompt: {
		name: string;
		command: string;
		content: string;
		tags: string[];
		access_grants: any[];
	} | null = null;

	let clone = false;

	const onSubmit = async (_prompt) => {
		const res = await createNewPrompt(localStorage.token, _prompt).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Prompt created successfully'));

			await prompts.set(await getPrompts(localStorage.token));
			await goto('/workspace/prompts');
		}
	};

	onMount(async () => {
		window.addEventListener('message', async (event) => {
			console.log(event);
			if (
				!['https://openwebui.com', 'https://www.openwebui.com', 'http://localhost:9999'].includes(
					event.origin
				)
			)
				return;
			const _prompt = JSON.parse(event.data);
			console.log('Received prompt via window message:', _prompt);

			clone = true;
			prompt = {
				name: _prompt.name || _prompt.title || 'Prompt',
				command: _prompt.command,
				content: _prompt.content,
				tags: _prompt.tags || [],
				access_grants: _prompt.access_grants !== undefined ? _prompt.access_grants : []
			};
		});

		if (window.opener ?? false) {
			window.opener.postMessage('loaded', '*');
		}

		if (sessionStorage.prompt) {
			const _prompt = JSON.parse(sessionStorage.prompt);
			sessionStorage.removeItem('prompt');

			console.log('Received prompt via sessionStorage:', _prompt);

			clone = true;
			prompt = {
				name: _prompt.name || _prompt.title || 'Prompt',
				command: _prompt.command,
				content: _prompt.content,
				tags: _prompt.tags || [],
				access_grants: _prompt.access_grants !== undefined ? _prompt.access_grants : []
			};
		}
	});
</script>

{#key prompt}
	<PromptEditor {prompt} {onSubmit} {clone} />
{/key}
