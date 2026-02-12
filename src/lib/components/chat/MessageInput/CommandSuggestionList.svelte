<script lang="ts">
	import { knowledge, prompts } from '$lib/stores';

	import { getPrompts } from '$lib/apis/prompts';
	import { getKnowledgeBases } from '$lib/apis/knowledge';

	import Prompts from './Commands/Prompts.svelte';
	import Knowledge from './Commands/Knowledge.svelte';
	import Models from './Commands/Models.svelte';
	import Skills from './Commands/Skills.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	import { onMount } from 'svelte';

	export let char = '';
	export let query = '';
	export let command: (payload: { id: string; label: string }) => void;

	export let onSelect = (e) => {};
	export let onUpload = (e) => {};
	export let insertTextHandler = (text) => {};

	let suggestionElement = null;
	let loading = false;
	let filteredItems = [];

	const init = async () => {
		loading = true;
		await Promise.all([
			(async () => {
				prompts.set(await getPrompts(localStorage.token));
			})()
		]);
		loading = false;
	};

	onMount(() => {
		init();
	});

	const onKeyDown = (event: KeyboardEvent) => {
		if (!['ArrowUp', 'ArrowDown', 'Enter', 'Tab', 'Escape'].includes(event.key)) return false;

		if (event.key === 'ArrowUp') {
			suggestionElement?.selectUp();
			const item = document.querySelector(`[data-selected="true"]`);
			item?.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
			return true;
		}
		if (event.key === 'ArrowDown') {
			suggestionElement?.selectDown();
			const item = document.querySelector(`[data-selected="true"]`);
			item?.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
			return true;
		}
		if (event.key === 'Enter' || event.key === 'Tab') {
			suggestionElement?.select();

			if (event.key === 'Enter') {
				event.preventDefault();
			}
			return true;
		}
		if (event.key === 'Escape') {
			return true;
		}
		return false;
	};

	// This method will be called from the suggestion renderer
	// @ts-ignore
	export function _onKeyDown(event: KeyboardEvent) {
		return onKeyDown(event);
	}
</script>

<div
	class="{(filteredItems ?? []).length > 0
		? ''
		: 'hidden'} rounded-2xl shadow-lg border border-gray-200 dark:border-gray-800 flex flex-col bg-white dark:bg-gray-850 w-72 p-1"
	id="suggestions-container"
>
	<div class="overflow-y-auto scrollbar-thin max-h-60">
		{#if !loading}
			{#if char === '/'}
				<Prompts
					bind:this={suggestionElement}
					{query}
					bind:filteredItems
					prompts={$prompts ?? []}
					onSelect={(e) => {
						const { type, data } = e;

						if (type === 'prompt') {
							insertTextHandler(data.content);
						}
					}}
				/>
			{:else if char === '#'}
				<Knowledge
					bind:this={suggestionElement}
					{query}
					bind:filteredItems
					onSelect={(e) => {
						const { type, data } = e;

						if (type === 'knowledge') {
							insertTextHandler('');

							onUpload({
								type: 'file',
								data: data
							});
						} else if (type === 'web') {
							insertTextHandler('');

							onUpload({
								type: 'web',
								data: data
							});
						}
					}}
				/>
			{:else if char === '@'}
				<Models
					bind:this={suggestionElement}
					{query}
					bind:filteredItems
					onSelect={(e) => {
						const { type, data } = e;

						if (type === 'model') {
							insertTextHandler('');

							onSelect({
								type: 'model',
								data: data
							});
						}
					}}
				/>
			{:else if char === '$'}
				<Skills
					bind:this={suggestionElement}
					{query}
					bind:filteredItems
					onSelect={(e) => {
						const { type, data } = e;

						if (type === 'skill') {
							command({
								id: `${data.id}|${data.name}`,
								label: data.name
							});

							onSelect({
								type: 'skill',
								data: data
							});
						}
					}}
				/>
			{/if}
		{:else}
			<div class="py-4 flex flex-col w-full rounded-xl text-gray-700 dark:text-gray-300">
				<Spinner />
			</div>
		{/if}
	</div>
</div>
