<script lang="ts">
	import { createEventDispatcher, getContext, onMount } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	export let show = false;
	export let variables: string[] = [];
	export let subtitle: string = '';
	export let promptRawContent = '';

	let variableValues: { [key: string]: string } = {};

	$: formattedPromptDisplay = (() => {
		if (!promptRawContent) {
			return '';
		}

		// Escape HTML tags in promptRawContent
		let escapedPrompt = promptRawContent.replace(/</g, '&lt;').replace(/>/g, '&gt;');

		if (variables && variables.length > 0) {
			variables.forEach((variable) => {
				const regex = new RegExp(`{{\\s*${variable}\\s*}}`, 'g');
				escapedPrompt = escapedPrompt.replace(regex, `<strong>{{${variable}}}</strong>`);
			});
		}
		return escapedPrompt;
	})();

	$: {
		const newValues = {};
		for (const variable of variables) {
			newValues[variable] = variableValues[variable] || '';
		}
		variableValues = newValues;
	}

	const handleSubmit = () => {
		dispatch('submit', variableValues);
		show = false;
	};

	let modalElement;

	onMount(() => {
		if (variables.length > 0 && modalElement) {
			const firstInput = modalElement.querySelector('input, textarea');
			if (firstInput) {
				(firstInput as HTMLElement).focus();
			}
		}
	});
</script>

<Modal bind:show size="lg" containerClassName="p-3" className="bg-white dark:bg-gray-900 rounded-2xl">
	<div bind:this={modalElement}>
		<div class="flex justify-between items-center dark:text-gray-300 px-5 pt-4 pb-2">
			<h2 class="text-lg font-medium self-center">{$i18n.t('Enter Variable Values')}</h2>
			<button
				class="self-center text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
				on:click={() => (show = false)}
				aria-label={$i18n.t('Close')}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>
		{#if subtitle}
			<p class="text-sm text-gray-600 dark:text-gray-400 mt-1 px-5">{@html subtitle}</p>
		{/if}

		{#if promptRawContent}
			<div
				class="max-h-56 overflow-y-auto bg-gray-50 dark:bg-gray-800 p-2 rounded-md my-3 text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap break-words mx-5"
			>
				{@html formattedPromptDisplay}
			</div>
		{/if}

		<p class="text-sm text-gray-600 dark:text-gray-400 mt-3 px-5">{$i18n.t('You may replace the placeholder variables with values below. Note that if you do not enter a value, the placeholder will be removed from the text.')}</p>

		<div class="p-5 max-h-[60vh] overflow-y-auto">
			{#each variables as variable (variable)}
				<div class="flex flex-col mb-4">
					<div class="text-sm text-gray-700 dark:text-gray-300">
						{@html $i18n.t('Insert a value for <strong class="font-semibold text-gray-800 dark:text-gray-100">{{variable}}</strong>', { variable })}
					</div>
					<Textarea
						id="variable-{variable}"
						class="w-full bg-gray-50 dark:bg-gray-800 border-gray-300 dark:border-gray-700 rounded-md p-2 text-sm dark:text-gray-100 focus:ring-blue-500 focus:border-blue-500 mt-1"
						placeholder={$i18n.t('Enter value here')}
						bind:value={variableValues[variable]}
						rows={2}
						on:keydown={(e) => {
							if (e.key === 'Enter' && !e.shiftKey) {
								e.preventDefault();
							}
						}}
					/>
				</div>
			{/each}
		</div>

		<div class="px-5 py-4 flex justify-end space-x-2">
			<button
				type="button"
				class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
				on:click={() => (show = false)}
			>
				{$i18n.t('Cancel')}
			</button>
			<button
				type="button"
				class="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
				on:click={handleSubmit}
			>
				{$i18n.t('Submit')}
			</button>
		</div>
	</div>
</Modal>
