<script>
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { prompts } from '$lib/stores';
	import { onMount, tick, getContext } from 'svelte';

	import { createNewPrompt, getPrompts } from '$lib/apis/prompts';
	import PromptEditor from '$lib/components/workspace/Prompts/PromptEditor.svelte';

	let prompt = null;
	const onSubmit = async ({ title, command, content }) => {
		const prompt = await createNewPrompt(localStorage.token, command, title, content).catch(
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
				content: _prompt.content
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
				content: _prompt.content
			};
			sessionStorage.removeItem('prompt');
		}
	});
</script>

{#key prompt}
	<PromptEditor {prompt} {onSubmit} />
{/key}
