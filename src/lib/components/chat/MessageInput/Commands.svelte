<script>
	import { createEventDispatcher, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	const dispatch = createEventDispatcher();

	import { knowledge, prompts } from '$lib/stores';

	import { removeLastWordFromString } from '$lib/utils';
	import { getPrompts } from '$lib/apis/prompts';
	import { getKnowledgeBases } from '$lib/apis/knowledge';

	import Prompts from './Commands/Prompts.svelte';
	import Knowledge from './Commands/Knowledge.svelte';
	import Models from './Commands/Models.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	export let prompt = '';
	export let files = [];

	let loading = false;
	let commandElement = null;

	export const selectUp = () => {
		commandElement?.selectUp();
	};

	export const selectDown = () => {
		commandElement?.selectDown();
	};

	let command = '';
	$: command = prompt?.split('\n').pop()?.split(' ')?.pop() ?? '';

	let show = false;
	$: show = ['/', '#', '@'].includes(command?.charAt(0)) || '\\#' === command.slice(0, 2);

	$: if (show) {
		init();
	}

	const init = async () => {
		loading = true;
		await Promise.all([
			(async () => {
				prompts.set(await getPrompts(localStorage.token));
			})(),
			(async () => {
				knowledge.set(await getKnowledgeBases(localStorage.token));
			})()
		]);
		loading = false;
	};
</script>

{#if show}
	{#if !loading}
		{#if command?.charAt(0) === '/'}
			<Prompts bind:this={commandElement} bind:prompt bind:files {command} />
		{:else if (command?.charAt(0) === '#' && command.startsWith('#') && !command.includes('# ')) || ('\\#' === command.slice(0, 2) && command.startsWith('#') && !command.includes('# '))}
			<Knowledge
				bind:this={commandElement}
				bind:prompt
				command={command.includes('\\#') ? command.slice(2) : command}
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
					if (files.find((f) => f.id === e.detail.id)) {
						return;
					}

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
	{:else}
		<div
			id="commands-container"
			class="px-2 mb-2 text-left w-full absolute bottom-0 left-0 right-0 z-10"
		>
			<div class="flex w-full rounded-xl border border-gray-50 dark:border-gray-850">
				<div
					class="max-h-60 flex flex-col w-full rounded-xl bg-white dark:bg-gray-900 dark:text-gray-100"
				>
					<Spinner />
				</div>
			</div>
		</div>
	{/if}
{/if}
