<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { prompts } from '$lib/stores';
	import { onMount, tick, getContext } from 'svelte';

	const i18n = getContext('i18n');

	import { getPromptByCommand, getPrompts, updatePromptByCommand } from '$lib/apis/prompts';
	import { getSessionUser } from '$lib/apis/auths';
	import { page } from '$app/stores';

	import PromptEditor from '$lib/components/workspace/Prompts/PromptEditor.svelte';

	let prompt = null;
	let disabled = false;

	const onSubmit = async (_prompt) => {
		console.log(_prompt);
		const prompt = await updatePromptByCommand(localStorage.token, _prompt).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (prompt) {
			toast.success($i18n.t('Prompt updated successfully'));
			await prompts.set(await getPrompts(localStorage.token));
			await goto('/workspace/prompts');
		}
	};

	onMount(async () => {
		const command = $page.url.searchParams.get('command');
		if (command) {
			// First attempt to load prompt
			const _prompt = await getPromptByCommand(
				localStorage.token,
				command.replace(/\//g, '')
			).catch(async (error) => {
				// If unauthorized, try to refresh session and retry once
				if (error?.toString().includes('401') || error?.toString().includes('Unauthorized')) {
					try {
						// Validate/refresh session
						await getSessionUser(localStorage.token);
						// Retry loading prompt
						return await getPromptByCommand(localStorage.token, command.replace(/\//g, ''));
					} catch (refreshError) {
						// Session refresh failed - redirect will be handled by layout
						console.log('Session validation failed:', refreshError);
						return null;
					}
				}
				// Non-401 error or retry failed
				console.error('Failed to load prompt:', error);
				toast.error(`${error}`);
				return null;
			});

			if (_prompt) {
				disabled = !_prompt.write_access ?? true;
				prompt = {
					title: _prompt.title,
					command: _prompt.command,
					content: _prompt.content,
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
