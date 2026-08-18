<script lang="ts">
	import { getContext, tick } from 'svelte';
	const i18n = getContext('i18n');

	import LightBulb from '$lib/components/icons/LightBulb.svelte';

	export let id = '';

	export let actions = [];
	export let onSetInputText = (text) => {};
	export let onExplain = (text: string) => {};

	let floatingInput = false;
	let selectedAction = null;

	let selectedText = '';
	let floatingInputValue = '';

	$: if (actions.length === 0) {
		actions = DEFAULT_ACTIONS;
	}

	const DEFAULT_ACTIONS = [
		{
			id: 'explain',
			label: $i18n.t('Explain'),
			icon: LightBulb,
			prompt: `{{SELECTED_CONTENT}}\n\n\n${$i18n.t('Explain')}`
		}
	];

	const actionHandler = (actionId) => {
		if (actionId === 'explain' && onExplain) {
			onExplain(selectedText);
			closeHandler();
			return;
		}

		let selectedContent = selectedText
			.split('\n')
			.map((line) => `> ${line}`)
			.join('\n');

		let selectedAction = actions.find((action) => action.id === actionId);
		if (!selectedAction) {
			return;
		}

		let prompt = selectedAction?.prompt ?? '';

		// Handle: {{variableId|tool:id="toolId"}} pattern
		// This regex captures variableId and toolId from {{variableId|tool:id="toolId"}}
		const varToolPattern = /\{\{(.*?)\|tool:id="([^"]+)"\}\}/g;
		prompt = prompt.replace(varToolPattern, (match, variableId, toolId) => {
			return variableId; // Replace with just variableId
		});

		// legacy {{TOOL:toolId}} pattern (for backward compatibility)
		let toolIdPattern = /\{\{TOOL:([^\}]+)\}\}/g;

		// Remove all TOOL placeholders from the prompt
		prompt = prompt.replace(toolIdPattern, '');

		if (prompt.includes('{{INPUT_CONTENT}}') && floatingInput) {
			prompt = prompt.replace('{{INPUT_CONTENT}}', floatingInputValue);
			floatingInputValue = '';
		}

		prompt = prompt.replace('{{CONTENT}}', selectedText);
		prompt = prompt.replace('{{SELECTED_CONTENT}}', selectedContent);

		// Prepopulate the main chat input instead of inline streaming
		onSetInputText(prompt);
		closeHandler();
	};

	export const setSelectedText = (text: string) => {
		if (text) {
			selectedText = text;
		}
	};

	export const closeHandler = () => {
		selectedAction = null;
		selectedText = '';
		floatingInput = false;
		floatingInputValue = '';
	};
</script>

<div
	id={`floating-buttons-${id}`}
	class="absolute rounded-lg mt-1 text-xs z-9999"
	style="display: none"
>
	{#if !floatingInput}
		<div
			class="flex flex-row shrink-0 p-1 bg-slate-900/95 text-white dark:bg-gray-800/95 text-xs font-medium rounded-xl shadow-2xl border border-sky-400/30 backdrop-blur-md"
		>
			{#each actions as action}
				<button
					aria-label={action.label}
					class="px-2.5 py-1 hover:bg-sky-500/20 text-sky-200 hover:text-white rounded-lg flex items-center gap-1.5 min-w-fit transition cursor-pointer font-semibold shadow-sm"
					on:mousedown={() => {
						const currentSelection = window.getSelection()?.toString();
						if (currentSelection) {
							selectedText = currentSelection;
						}
					}}
					on:click={async () => {
						const currentSelection = window.getSelection()?.toString();
						if (currentSelection) {
							selectedText = currentSelection;
						}
						selectedAction = action;
						actionHandler(action.id);
					}}
				>
					{#if action.icon}
						<svelte:component this={action.icon} className="size-3.5 shrink-0 text-amber-400" />
					{/if}
					<div class="shrink-0">{action.label}</div>
				</button>
			{/each}
		</div>
	{:else}
		<div
			class="py-1 flex dark:text-gray-100 bg-white dark:bg-gray-850 border border-gray-100 dark:border-gray-800 w-72 rounded-full shadow-xl"
		>
			<input
				type="text"
				id="floating-message-input"
				class="ml-5 bg-transparent outline-hidden w-full flex-1 text-sm"
				placeholder={$i18n.t('Ask a question')}
				aria-label={$i18n.t('Ask a question')}
				bind:value={floatingInputValue}
				on:keydown={(e) => {
					if (e.key === 'Enter') {
						actionHandler(selectedAction?.id);
					}
				}}
			/>

			<div class="ml-1 mr-1">
				<button
					aria-label={$i18n.t('Submit question')}
					class="{floatingInputValue !== ''
						? 'bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 '
						: 'text-white bg-gray-200 dark:text-gray-900 dark:bg-gray-700 disabled'} transition rounded-full p-1.5 m-0.5 self-center"
					on:click={() => {
						actionHandler(selectedAction?.id);
					}}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="size-4"
					>
						<path
							fill-rule="evenodd"
							d="M8 14a.75.75 0 0 1-.75-.75V4.56L4.03 7.78a.75.75 0 0 1-1.06-1.06l4.5-4.5a.75.75 0 0 1 1.06 0l4.5 4.5a.75.75 0 0 1-1.06 1.06L8.75 4.56v8.69A.75.75 0 0 1 8 14Z"
							clip-rule="evenodd"
						/>
					</svg>
				</button>
			</div>
		</div>
	{/if}
</div>
