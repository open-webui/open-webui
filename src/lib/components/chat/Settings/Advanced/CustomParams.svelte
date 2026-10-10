<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as I18n } from 'i18next';
	import { v4 as uuidv4 } from 'uuid';
	import Plus from '$lib/components/icons/Plus.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	const i18n = getContext<Writable<I18n>>('i18n');
	export let compact = false;
	export let value: Record<string, unknown> = {};
	const id = `custom-params-${uuidv4()}`;

	// Suggestions only; support depends on the provider and model.
	// OpenAI: https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create
	// OpenRouter: https://openrouter.ai/docs/api_reference/parameters
	// Ollama: https://docs.ollama.com/modelfile and https://docs.ollama.com/api/chat
	const suggestions: Record<string, string[]> = {
		service_tier: ['auto', 'default', 'flex', 'priority', 'fast'],
		reasoning_effort: ['none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max'],
		reasoning: ['{"effort":"low"}', '{"effort":"medium"}', '{"effort":"high"}'],
		verbosity: ['low', 'medium', 'high'],
		text: ['{"verbosity":"low"}', '{"verbosity":"medium"}', '{"verbosity":"high"}'],
		max_completion_tokens: [],
		max_output_tokens: [],
		max_tokens: [],
		parallel_tool_calls: ['true', 'false'],
		tool_choice: ['auto', 'none', 'required'],
		response_format: ['{"type":"text"}', '{"type":"json_object"}'],
		temperature: [],
		top_p: [],
		top_k: [],
		min_p: [],
		frequency_penalty: [],
		presence_penalty: [],
		repetition_penalty: [],
		repeat_penalty: [],
		seed: [],
		stop: [],
		logprobs: ['true', 'false'],
		top_logprobs: [],
		prompt_cache_key: [],
		prompt_cache_options: ['{"mode":"implicit","ttl":"30m"}', '{"mode":"explicit","ttl":"30m"}'],
		store: ['true', 'false'],
		provider: ['{"sort":"price"}', '{"sort":"throughput"}', '{"sort":"latency"}'],
		num_ctx: [],
		num_predict: [],
		think: ['true', 'false'],
		format: ['json'],
		keep_alive: []
	};

	const focusNew = (node: HTMLInputElement, empty: boolean) => {
		if (empty) node.focus();
	};
</script>

<div class="flex flex-col justify-center">
	<datalist id={`${id}-names`}>
		{#each Object.keys(suggestions) as name}
			{#if !Object.hasOwn(value ?? {}, name)}
				<option value={name}></option>
			{/if}
		{/each}
	</datalist>
	<div class="min-w-0 flex-1">
		{#each Object.keys(value ?? {}) as key, index}
			{@const options = Object.hasOwn(suggestions, key) ? suggestions[key] : []}
			<div
				class={compact
					? 'mb-1 grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] items-start gap-3 py-1'
					: 'mb-1 grid grid-cols-[1fr_auto] items-center gap-y-0.5 py-0.5'}
			>
				<label class="min-w-0">
					{#if compact}<span class="block text-xs font-normal text-gray-600 dark:text-gray-400"
							>{$i18n.t('Parameter')}</span
						>{/if}
					<input
						type="text"
						class={compact
							? 'w-full min-w-0 bg-transparent py-1 text-[0.8125rem] font-normal text-gray-900 outline-none placeholder:text-gray-300 dark:text-gray-100 dark:placeholder:text-gray-700'
							: 'min-w-0 w-full bg-transparent text-xs font-normal text-gray-900 dark:text-gray-100 outline-none'}
						aria-label={$i18n.t('Custom Parameter Name')}
						list={`${id}-names`}
						autocomplete="off"
						placeholder={compact ? $i18n.t('e.g. temperature') : $i18n.t('Custom Parameter Name')}
						required
						pattern={'.*\\S.*'}
						use:focusNew={key === ''}
						title={key}
						value={key}
						on:change={(event) => {
							const name = event.currentTarget.value.trim();
							if (name && name !== key) {
								value[name] = value[key];
								delete value[key];
								value = { ...value };
							}
						}}
					/>
				</label>
				<label class={compact ? 'min-w-0' : 'order-last col-span-2'}>
					{#if compact}<span class="block text-xs font-normal text-gray-600 dark:text-gray-400"
							>{$i18n.t('Value')}</span
						>{/if}
					<input
						type="text"
						class={compact
							? 'w-full min-w-0 bg-transparent py-1 text-[0.8125rem] font-normal text-gray-900 outline-none placeholder:text-gray-300 dark:text-gray-100 dark:placeholder:text-gray-700'
							: 'w-full min-w-0 bg-transparent text-[0.8125rem] font-normal text-gray-900 dark:text-gray-100 outline-none'}
						aria-label={$i18n.t('Custom Parameter Value')}
						list={options.length ? `${id}-values-${index}` : undefined}
						autocomplete="off"
						placeholder={compact ? $i18n.t('e.g. 0.7') : $i18n.t('Custom Parameter Value')}
						value={typeof value[key] === 'object' ? JSON.stringify(value[key]) : value[key]}
						on:input={(event) => (value = { ...value, [key]: event.currentTarget.value })}
					/>
					{#if options.length}
						<datalist id={`${id}-values-${index}`}>
							{#each options as option}
								<option value={option}></option>
							{/each}
						</datalist>
					{/if}
				</label>
				<button
					type="button"
					class={compact
						? 'mt-4 flex h-5 w-3 items-center justify-center rounded text-gray-400 hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-300'
						: 'flex shrink-0 rounded-sm p-1 px-3 text-xs outline-hidden transition'}
					aria-label={`${$i18n.t('Remove')} ${key || $i18n.t('parameter')}`}
					on:click={() => {
						delete value[key];
						value = { ...value };
					}}
				>
					{#if compact}<XMark className="size-3" />{:else}{$i18n.t('Remove')}{/if}
				</button>
			</div>
		{/each}
	</div>
	<button
		type="button"
		class={compact
			? 'flex w-fit items-center gap-1.5 whitespace-nowrap py-1 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 disabled:opacity-40'
			: 'mt-1 mb-5 flex w-full items-center justify-center gap-2 text-center'}
		aria-label={$i18n.t('Add Custom Parameter')}
		title={$i18n.t('Add Custom Parameter')}
		disabled={Object.hasOwn(value ?? {}, '')}
		on:click={() => {
			value = value ?? {};
			value = { ...value, '': '' };
		}}
	>
		<Plus className="size-3" strokeWidth="1.5" /><span
			>{compact ? $i18n.t('Add parameter') : $i18n.t('Add Custom Parameter')}</span
		>
	</button>
</div>
