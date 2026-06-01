<script lang="ts">
	import { getContext, tick } from 'svelte';
	const i18n = getContext('i18n');

	import ChatBubble from '$lib/components/icons/ChatBubble.svelte';
	import LightBulb from '$lib/components/icons/LightBulb.svelte';

	export let id = '';

	export let actions = [];
	export let onSetInputText = (text) => {};

	let floatingInput = false;
	let selectedAction = null;

	let selectedText = '';
	let floatingInputValue = '';

	$: if (actions.length === 0) {
		actions = DEFAULT_ACTIONS;
	}

	const DEFAULT_ACTIONS = [
		{
			id: 'ask',
			label: $i18n.t('Ask'),
			icon: ChatBubble,
			input: true,
			prompt: `{{SELECTED_CONTENT}}\n\n\n{{INPUT_CONTENT}}`
		},
		{
			id: 'explain',
			label: $i18n.t('Explain'),
			icon: LightBulb,
			prompt: `{{SELECTED_CONTENT}}\n\n\n${$i18n.t('Explain')}`
		}
	];

	const actionHandler = (actionId) => {
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
			class="flex flex-row shrink-0 p-0.5 bg-white dark:bg-gray-850 dark:text-gray-100 text-medium rounded-xl shadow-xl border border-gray-100 dark:border-gray-800"
		>
			{#each actions as action}
				<button
					aria-label={action.label}
					class="px-1.5 py-[1px] hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl flex items-center gap-1 min-w-fit transition"
					on:click={async () => {
						selectedText = window.getSelection().toString();
						selectedAction = action;

						if (action.prompt.includes('{{INPUT_CONTENT}}')) {
							floatingInput = true;
							floatingInputValue = '';

							await tick();
							setTimeout(() => {
								const input = document.getElementById('floating-message-input');
								if (input) {
									input.focus();
								}
							}, 0);
						} else {
							actionHandler(action.id);
						}
					}}
				>
					{#if action.icon}
						<svelte:component this={action.icon} className="size-3 shrink-0" />
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
