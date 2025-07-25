<script lang="ts">
	import { createEventDispatcher, getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	
	import RichTextInput from '$lib/components/common/RichTextInput.svelte';
	import { processInputText, extractVariablesFromText } from '../utils/textProcessing';
	import { generateAutoCompletion } from '$lib/apis';
	import type { InputVariable } from '../types';
	
	export let value = '';
	export let placeholder = '';
	export let disabled = false;
	export let autoFocus = true;
	export let transparentBackground = false;
	export let selectedModels: string[] = [];
	export let variables: Record<string, string> = {};
	
	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();
	
	let richTextInput: any;
	let extractedVariables: InputVariable[] = [];
	
	$: {
		// Extract variables when text changes
		extractedVariables = extractVariablesFromText(value);
		if (extractedVariables.length > 0) {
			dispatch('variablesFound', extractedVariables);
		}
	}
	
	function handleInput(event: CustomEvent) {
		value = event.detail;
		dispatch('input', value);
	}
	
	function handleKeyDown(event: KeyboardEvent) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			handleSubmit();
		} else if (event.key === 'Tab' && !event.shiftKey && !event.ctrlKey) {
			// Handle auto-completion
			event.preventDefault();
			handleAutoComplete();
		}
		
		dispatch('keydown', event);
	}
	
	function handleSubmit() {
		const processedText = processInputText(value, { variables });
		dispatch('submit', processedText);
	}
	
	async function handleAutoComplete() {
		if (!value.trim() || selectedModels.length === 0) return;
		
		try {
			const result = await generateAutoCompletion({
				prompt: value,
				model: selectedModels[0]
			});
			
			if (result?.text) {
				value += result.text;
				dispatch('input', value);
			}
		} catch (error) {
			console.error('Auto-completion error:', error);
		}
	}
	
	export function setText(text: string) {
		value = text;
		if (richTextInput?.setText) {
			richTextInput.setText(text);
		}
	}
	
	export function insertText(text: string) {
		if (richTextInput?.insertText) {
			richTextInput.insertText(text);
		} else {
			value += text;
		}
		dispatch('input', value);
	}
	
	export function focus() {
		richTextInput?.focus();
	}
	
	export function blur() {
		richTextInput?.blur();
	}
	
	onMount(() => {
		if (autoFocus) {
			focus();
		}
	});
</script>

<div class="w-full">
	<RichTextInput
		bind:this={richTextInput}
		bind:value
		{placeholder}
		{disabled}
		{transparentBackground}
		on:input={handleInput}
		on:keydown={handleKeyDown}
		on:paste
		on:focus
		on:blur
		className="min-h-[44px] max-h-[200px] {transparentBackground ? '' : 'px-3 py-2'}"
	/>
	
	{#if extractedVariables.length > 0}
		<div class="mt-1 text-xs text-gray-500 dark:text-gray-400">
			{$i18n.t('Variables found')}: {extractedVariables.map(v => v.name).join(', ')}
		</div>
	{/if}
</div>