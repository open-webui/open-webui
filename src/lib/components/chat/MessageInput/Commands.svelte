<script>
	import { createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';

	const dispatch = createEventDispatcher();

	import Prompts from './Commands/Prompts.svelte';
	import Knowledge from './Commands/Knowledge.svelte';
	import Models from './Commands/Models.svelte';

	import { removeLastWordFromString } from '$lib/utils';
	import { processWeb, processYoutubeVideo } from '$lib/apis/retrieval';

	export let prompt = '';
	export let files = [];

	let commandElement = null;

	export const selectUp = () => {
		commandElement?.selectUp();
	};

	export const selectDown = () => {
		commandElement?.selectDown();
	};

	let command = '';
	$: command = (prompt?.trim() ?? '').split(' ')?.at(-1) ?? '';
</script>

{#if ['/', '#', '@'].includes(command?.charAt(0))}
	{#if command?.charAt(0) === '/'}
		<Prompts bind:this={commandElement} bind:prompt bind:files {command} />
	{:else if command?.charAt(0) === '#'}
		<Knowledge
			bind:this={commandElement}
			bind:prompt
			{command}
			on:youtube={(e) => {
				console.log(e);
				dispatch('upload', {
					type: 'youtube',
					data: e.detail
				});
			}}
			on:url={(e) => {
				console.log(e);
				dispatch('upload', {
					type: 'web',
					data: e.detail
				});
			}}
			on:select={(e) => {
				console.log(e);
				files = [
					...files,
					{
						...e.detail,
						status: 'processed'
					}
				];

				dispatch('select');
			}}
		/>
	{:else if command?.charAt(0) === '@'}
		<Models
			bind:this={commandElement}
			{command}
			on:select={(e) => {
				prompt = removeLastWordFromString(prompt, command);

				dispatch('select', {
					type: 'model',
					data: e.detail
				});
			}}
		/>
	{/if}
{/if}
