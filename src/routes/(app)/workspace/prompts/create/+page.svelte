<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { prompts } from '$lib/stores';
	import { onMount, tick, getContext } from 'svelte';

	const i18n = getContext('i18n');

	import { createNewPrompt, getPrompts } from '$lib/apis/prompts';
	import PromptEditor from '$lib/components/workspace/Prompts/PromptEditor.svelte';

	let prompt = null;
	const onSubmit = async (_prompt) => {
		const prompt = await createNewPrompt(localStorage.token, _prompt).catch((error) => {
			toast.error(error);
			return null;
		});

		if (prompt) {
			toast.success($i18n.t('Prompt created successfully'));

			await prompts.set(await getPrompts(localStorage.token));
			await goto('/workspace/prompts');
		}
	};

	onMount(async () => {
		window.addEventListener('message', async (event) => {
			if (
				!['https://openwebui.com', 'https://www.openwebui.com', 'http://localhost:5173'].includes(
					event.origin
				)
			)
				return;
			const _prompt = JSON.parse(event.data);
			console.log(_prompt);

			prompt = {
				title: _prompt.title,
				command: _prompt.command,
				content: _prompt.content,
				access_control: null
			};
		});

		if (window.opener ?? false) {
			window.opener.postMessage('loaded', '*');
		}

		if (sessionStorage.prompt) {
			const _prompt = JSON.parse(sessionStorage.prompt);

			prompt = {
				title: _prompt.title,
				command: _prompt.command,
				content: _prompt.content,
				access_control: null
			};
			sessionStorage.removeItem('prompt');
		}
	});
</script>

{#key prompt}
	<PromptEditor {prompt} {onSubmit} />
{/key}
