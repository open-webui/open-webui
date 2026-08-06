<script lang="ts">
	import Switch from '$lib/components/common/Switch.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import type { i18n as i18nType } from 'i18next';
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let onChange: (params: any) => void = () => {};

	export let admin = false;
	export let custom = false;
	export let layout: 'stack' | 'grid' = 'stack';

	const defaultParams = {
		// Advanced
		stream_response: null, // Set stream responses for this model individually
		stream_delta_chunk_size: null, // Set the chunk size for streaming responses
		compact_token_threshold: null,
		function_calling: null,
		reasoning_tags: null,
		seed: null,
		stop: null,
		temperature: null,
		reasoning_effort: null,
		logit_bias: null,
		max_tokens: null,
		top_k: null,
		top_p: null,
		min_p: null,
		frequency_penalty: null,
		presence_penalty: null,
		mirostat: null,
		mirostat_eta: null,
		mirostat_tau: null,
		repeat_last_n: null,
		tfs_z: null,
		repeat_penalty: null,
		use_mmap: null,
		use_mlock: null,
		think: null,
		format: null,
		keep_alive: null,
		num_keep: null,
		num_ctx: null,
		num_batch: null,
		num_thread: null,
		num_gpu: null
	};
	type RangeParamKey = keyof typeof defaultParams;

	export let params: any = defaultParams;
	$: if (params) {
		onChange(params);
	}

	const setTopK = (event: Event) => {
		const input = event.currentTarget as HTMLInputElement;
		const rawValue = input.value;
		const value = Number(rawValue);

		if (!/^\d+$/.test(rawValue) || value < 0 || value > 1000) {
			input.value = `${params.top_k ?? ''}`;
			return;
		}

		params.top_k = value;
	};
</script>

{#snippet rangeParam(
	key: RangeParamKey,
	label: string,
	min: number,
	max: number,
	rangeStep: number | string,
	numberStep: number | string = 'any',
	numberMax: number | undefined = max
)}
	<div class="flex mt-0.5 space-x-2">
		<div class=" flex-1">
			<input
				type="range"
				aria-label={label}
				{min}
				{max}
				step={rangeStep}
				bind:value={params[key]}
				class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
			/>
		</div>
		<div>
			<input
				bind:value={params[key]}
				type="number"
				aria-label={label}
				class=" bg-transparent text-center w-14"
				{min}
				max={numberMax}
				step={numberStep}
			/>
		</div>
	</div>
{/snippet}

<div
	class={layout === 'grid'
		? 'grid grid-cols-1 gap-x-5 gap-y-1 pb-safe-bottom text-xs text-gray-600 dark:text-gray-400 sm:grid-cols-2 lg:grid-cols-3'
		: 'space-y-1 pb-safe-bottom text-xs text-gray-600 dark:text-gray-400'}
>
	<div>
		<Tooltip
			content={$i18n.t(
				'When enabled, the model will respond to each chat message in real-time, generating a response as soon as the user sends a message. This mode is useful for live chat applications, but may impact performance on slower hardware.'
			)}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class=" py-0.5 flex w-full justify-between">
				<div class=" self-center text-xs">
					{$i18n.t('Stream Chat Response')}
				</div>
				<button
					class="p-1 px-3 text-xs flex rounded-sm transition"
					on:click={() => {
						params.stream_response =
							(params?.stream_response ?? null) === null
								? true
								: params.stream_response
									? false
									: null;
					}}
					type="button"
				>
					{#if params.stream_response === true}
						<span class="ml-2 self-center">{$i18n.t('On')}</span>
					{:else if params.stream_response === false}
						<span class="ml-2 self-center">{$i18n.t('Off')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Default')}</span>
					{/if}
				</button>
			</div>
		</Tooltip>
	</div>

	{#if admin}
		<div>
			<Tooltip
				content={$i18n.t(
					'The stream delta chunk size for the model. Increasing the chunk size will make the model respond with larger pieces of text at once.'
				)}
				placement="top-start"
				className="inline-tooltip"
			>
				<div class="flex w-full justify-between">
					<div class=" self-center text-xs">
						{$i18n.t('Stream Delta Chunk Size')}
					</div>
					<button
						class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
						type="button"
						on:click={() => {
							params.stream_delta_chunk_size =
								(params?.stream_delta_chunk_size ?? null) === null ? 1 : null;
						}}
					>
						{#if (params?.stream_delta_chunk_size ?? null) === null}
							<span class="ml-2 self-center"> {$i18n.t('Default')} </span>
						{:else}
							<span class="ml-2 self-center"> {$i18n.t('Custom')} </span>
						{/if}
					</button>
				</div>
			</Tooltip>

			{#if (params?.stream_delta_chunk_size ?? null) !== null}
				{@render rangeParam(
					'stream_delta_chunk_size',
					$i18n.t('Stream Delta Chunk Size'),
					1,
					128,
					1,
					'any',
					undefined
				)}
			{/if}
		</div>

		<div>
			<Tooltip
				content={$i18n.t(
					'Set a model-specific context compaction token threshold. When set, this overrides the global threshold up to the global cap.'
				)}
				placement="top-start"
				className="inline-tooltip"
			>
				<div class="flex w-full justify-between">
					<div class=" self-center text-xs">
						{$i18n.t('Context Compaction Threshold')}
					</div>
					<button
						class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
						type="button"
						on:click={() => {
							params.compact_token_threshold =
								(params?.compact_token_threshold ?? null) === null ? 80000 : null;
						}}
					>
						{#if (params?.compact_token_threshold ?? null) === null}
							<span class="ml-2 self-center"> {$i18n.t('Default')} </span>
						{:else}
							<span class="ml-2 self-center"> {$i18n.t('Custom')} </span>
						{/if}
					</button>
				</div>
			</Tooltip>

			{#if (params?.compact_token_threshold ?? null) !== null}
				<div class="flex mt-0.5 space-x-2">
					<div class=" flex-1">
						<input
							class="text-sm w-full bg-transparent outline-hidden outline-none"
							type="number"
							aria-label={$i18n.t('Context Compaction Threshold')}
							placeholder={$i18n.t('Enter token threshold')}
							bind:value={params.compact_token_threshold}
							autocomplete="off"
							min="1"
							step="1"
						/>
					</div>
				</div>
			{/if}
		</div>
	{/if}

	<div>
		<Tooltip
			content={$i18n.t(
				"Native mode (default) leverages the model's built-in tool-calling capabilities. Legacy mode works with a wider range of models by calling tools once before execution via prompt injection."
			)}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class=" py-0.5 flex w-full justify-between">
				<div class=" self-center text-xs">
					{$i18n.t('Function Calling')}
				</div>
				<button
					class="p-1 px-3 text-xs flex rounded-sm transition"
					on:click={() => {
						if ((params?.function_calling ?? null) === null) {
							params.function_calling = 'native';
						} else if (params.function_calling === 'native') {
							params.function_calling = 'legacy';
						} else {
							params.function_calling = null;
						}
					}}
					type="button"
				>
					{#if params.function_calling === 'native'}
						<span class="ml-2 self-center">{$i18n.t('Native')}</span>
					{:else if params.function_calling === 'legacy'}
						<span class="ml-2 self-center">{$i18n.t('Legacy')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Default')}</span>
					{/if}
				</button>
			</div>
		</Tooltip>
	</div>

	<div class=" py-0.5 w-full justify-between">
		<Tooltip
			content={$i18n.t(
				'Enable, disable, or customize the reasoning tags used by the model. "Enabled" uses default tags, "Disabled" turns off reasoning tags, and "Custom" lets you specify your own start and end tags.'
			)}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs">
					{$i18n.t('Reasoning Tags')}
				</div>
				<button
					class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
					type="button"
					on:click={() => {
						if ((params?.reasoning_tags ?? null) === null) {
							params.reasoning_tags = ['', ''];
						} else if ((params?.reasoning_tags ?? []).length === 2) {
							params.reasoning_tags = true;
						} else if ((params?.reasoning_tags ?? null) !== false) {
							params.reasoning_tags = false;
						} else {
							params.reasoning_tags = null;
						}
					}}
				>
					{#if (params?.reasoning_tags ?? null) === null}
						<span class="ml-2 self-center"> {$i18n.t('Default')} </span>
					{:else if (params?.reasoning_tags ?? null) === true}
						<span class="ml-2 self-center"> {$i18n.t('Enabled')} </span>
					{:else if (params?.reasoning_tags ?? null) === false}
						<span class="ml-2 self-center"> {$i18n.t('Disabled')} </span>
					{:else}
						<span class="ml-2 self-center"> {$i18n.t('Custom')} </span>
					{/if}
				</button>
			</div>
		</Tooltip>

		{#if ![true, false, null].includes(params?.reasoning_tags ?? null) && (params?.reasoning_tags ?? []).length === 2}
			<div class="flex mt-0.5 space-x-2">
				<div class=" flex-1">
					<input
						class="text-sm w-full bg-transparent outline-hidden outline-none"
						type="text"
						aria-label={$i18n.t('Start Tag')}
						placeholder={$i18n.t('Start Tag')}
						bind:value={params.reasoning_tags[0]}
						autocomplete="off"
					/>
				</div>

				<div class=" flex-1">
					<input
						class="text-sm w-full bg-transparent outline-hidden outline-none"
						type="text"
						aria-label={$i18n.t('End Tag')}
						placeholder={$i18n.t('End Tag')}
						bind:value={params.reasoning_tags[1]}
						autocomplete="off"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<Tooltip
			content={$i18n.t(
				'Sets the random number seed to use for generation. Setting this to a specific number will make the model generate the same text for the same prompt.'
			)}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs">
					{$i18n.t('Seed')}
				</div>

				<button
					class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
					type="button"
					on:click={() => {
						params.seed = (params?.seed ?? null) === null ? 0 : null;
					}}
				>
					{#if (params?.seed ?? null) === null}
						<span class="ml-2 self-center"> {$i18n.t('Default')} </span>
					{:else}
						<span class="ml-2 self-center"> {$i18n.t('Custom')} </span>
					{/if}
				</button>
			</div>
		</Tooltip>

		{#if (params?.seed ?? null) !== null}
			<div class="flex mt-0.5 space-x-2">
				<div class=" flex-1">
					<input
						class="text-sm w-full bg-transparent outline-hidden outline-none"
						type="number"
						aria-label={$i18n.t('Seed')}
						placeholder={$i18n.t('Enter Seed')}
						bind:value={params.seed}
						autocomplete="off"
						min="0"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<Tooltip
			content={$i18n.t(
				'Sets the stop sequences to use. When this pattern is encountered, the LLM will stop generating text and return. Multiple stop patterns may be set by specifying multiple separate stop parameters in a modelfile.'
			)}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs">
					{$i18n.t('Stop Sequence')}
				</div>

				<button
					class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
					type="button"
					on:click={() => {
						params.stop = (params?.stop ?? null) === null ? '' : null;
					}}
				>
					{#if (params?.stop ?? null) === null}
						<span class="ml-2 self-center"> {$i18n.t('Default')} </span>
					{:else}
						<span class="ml-2 self-center"> {$i18n.t('Custom')} </span>
					{/if}
				</button>
			</div>
		</Tooltip>

		{#if (params?.stop ?? null) !== null}
			<div class="flex mt-0.5 space-x-2">
				<div class=" flex-1">
					<input
						class="text-sm w-full bg-transparent outline-hidden outline-none"
						type="text"
						aria-label={$i18n.t('Stop Sequence')}
						placeholder={$i18n.t('Enter stop sequence')}
						bind:value={params.stop}
						autocomplete="off"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<Tooltip
			content={$i18n.t(
				'The temperature of the model. Increasing the temperature will make the model answer more creatively.'
			)}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs">
					{$i18n.t('Temperature')}
				</div>
				<button
					class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
					type="button"
					on:click={() => {
						params.temperature = (params?.temperature ?? null) === null ? 0.8 : null;
					}}
				>
					{#if (params?.temperature ?? null) === null}
						<span class="ml-2 self-center"> {$i18n.t('Default')} </span>
					{:else}
						<span class="ml-2 self-center"> {$i18n.t('Custom')} </span>
					{/if}
				</button>
			</div>
		</Tooltip>

		{#if (params?.temperature ?? null) !== null}
			{@render rangeParam('temperature', $i18n.t('Temperature'), 0, 2, 0.05)}
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<Tooltip
			content={$i18n.t(
				'Constrains effort on reasoning for reasoning models. Only applicable to reasoning models from specific providers that support reasoning effort.'
			)}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs">
					{$i18n.t('Reasoning Effort')}
				</div>
				<button
					class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
					type="button"
					on:click={() => {
						params.reasoning_effort = (params?.reasoning_effort ?? null) === null ? 'medium' : null;
					}}
				>
					{#if (params?.reasoning_effort ?? null) === null}
						<span class="ml-2 self-center"> {$i18n.t('Default')} </span>
					{:else}
						<span class="ml-2 self-center"> {$i18n.t('Custom')} </span>
					{/if}
				</button>
			</div>
		</Tooltip>

		{#if (params?.reasoning_effort ?? null) !== null}
			<div class="flex mt-0.5 space-x-2">
				<div class=" flex-1">
					<input
						class="text-sm w-full bg-transparent outline-hidden outline-none"
						type="text"
						aria-label={$i18n.t('Reasoning Effort')}
						placeholder={$i18n.t('Enter reasoning effort')}
						bind:value={params.reasoning_effort}
						autocomplete="off"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<Tooltip
			content={$i18n.t(
				'Boosting or penalizing specific tokens for constrained responses. Bias values will be clamped between -100 and 100 (inclusive). (Default: none)'
			)}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs">
					{'logit_bias'}
				</div>
				<button
					class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
					type="button"
					on:click={() => {
						params.logit_bias = (params?.logit_bias ?? null) === null ? '' : null;
					}}
				>
					{#if (params?.logit_bias ?? null) === null}
						<span class="ml-2 self-center"> {$i18n.t('Default')} </span>
					{:else}
						<span class="ml-2 self-center"> {$i18n.t('Custom')} </span>
					{/if}
				</button>
			</div>
		</Tooltip>

		{#if (params?.logit_bias ?? null) !== null}
			<div class="flex mt-0.5 space-x-2">
				<div class=" flex-1">
					<input
						class="text-sm w-full bg-transparent outline-hidden outline-none"
						type="text"
						aria-label="logit_bias"
						placeholder={$i18n.t(
							'Enter comma-separated "token:bias_value" pairs (example: 5432:100, 413:-100)'
						)}
						bind:value={params.logit_bias}
						autocomplete="off"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<Tooltip
			content={$i18n.t(
				'This option sets the maximum number of tokens the model can generate in its response. Increasing this limit allows the model to provide longer answers, but it may also increase the likelihood of unhelpful or irrelevant content being generated.'
			)}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs">
					{'max_tokens'}
				</div>

				<button
					class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
					type="button"
					on:click={() => {
						params.max_tokens = (params?.max_tokens ?? null) === null ? 128 : null;
					}}
				>
					{#if (params?.max_tokens ?? null) === null}
						<span class="ml-2 self-center">{$i18n.t('Default')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
					{/if}
				</button>
			</div>
		</Tooltip>

		{#if (params?.max_tokens ?? null) !== null}
			{@render rangeParam('max_tokens', 'max_tokens', -2, 131072, 1, 1, undefined)}
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<Tooltip
			content={$i18n.t(
				'Reduces the probability of generating nonsense. A higher value (e.g. 100) will give more diverse answers, while a lower value (e.g. 10) will be more conservative.'
			)}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs">
					{'top_k'}
				</div>
				<button
					class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
					type="button"
					on:click={() => {
						params.top_k = (params?.top_k ?? null) === null ? 40 : null;
					}}
				>
					{#if (params?.top_k ?? null) === null}
						<span class="ml-2 self-center">{$i18n.t('Default')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
					{/if}
				</button>
			</div>
		</Tooltip>

		{#if (params?.top_k ?? null) !== null}
			<div class="flex mt-0.5 space-x-2">
				<div class=" flex-1">
					<input
						type="range"
						aria-label="top_k"
						min="0"
						max="1000"
						step="1"
						value={params.top_k}
						on:input={setTopK}
						class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
					/>
				</div>
				<div>
					<input
						value={params.top_k}
						type="number"
						aria-label="top_k"
						class=" bg-transparent text-center w-14"
						min="0"
						max="1000"
						step="1"
						on:input={setTopK}
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<Tooltip
			content={$i18n.t(
				'Works together with top-k. A higher value (e.g., 0.95) will lead to more diverse text, while a lower value (e.g., 0.5) will generate more focused and conservative text.'
			)}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs">
					{'top_p'}
				</div>

				<button
					class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
					type="button"
					on:click={() => {
						params.top_p = (params?.top_p ?? null) === null ? 0.9 : null;
					}}
				>
					{#if (params?.top_p ?? null) === null}
						<span class="ml-2 self-center">{$i18n.t('Default')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
					{/if}
				</button>
			</div>
		</Tooltip>

		{#if (params?.top_p ?? null) !== null}
			{@render rangeParam('top_p', 'top_p', 0, 1, 0.05)}
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<Tooltip
			content={$i18n.t(
				'Alternative to the top_p, and aims to ensure a balance of quality and variety. The parameter p represents the minimum probability for a token to be considered, relative to the probability of the most likely token. For example, with p=0.05 and the most likely token having a probability of 0.9, logits with a value less than 0.045 are filtered out.'
			)}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs">
					{'min_p'}
				</div>
				<button
					class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
					type="button"
					on:click={() => {
						params.min_p = (params?.min_p ?? null) === null ? 0.0 : null;
					}}
				>
					{#if (params?.min_p ?? null) === null}
						<span class="ml-2 self-center">{$i18n.t('Default')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
					{/if}
				</button>
			</div>
		</Tooltip>

		{#if (params?.min_p ?? null) !== null}
			{@render rangeParam('min_p', 'min_p', 0, 1, 0.05)}
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<Tooltip
			content={$i18n.t(
				'Sets a scaling bias against tokens to penalize repetitions, based on how many times they have appeared. A higher value (e.g., 1.5) will penalize repetitions more strongly, while a lower value (e.g., 0.9) will be more lenient. At 0, it is disabled.'
			)}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs">
					{'frequency_penalty'}
				</div>

				<button
					class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
					type="button"
					on:click={() => {
						params.frequency_penalty = (params?.frequency_penalty ?? null) === null ? 1.1 : null;
					}}
				>
					{#if (params?.frequency_penalty ?? null) === null}
						<span class="ml-2 self-center">{$i18n.t('Default')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
					{/if}
				</button>
			</div>
		</Tooltip>

		{#if (params?.frequency_penalty ?? null) !== null}
			{@render rangeParam('frequency_penalty', 'frequency_penalty', -2, 2, 0.05)}
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<Tooltip
			content={$i18n.t(
				'Sets a flat bias against tokens that have appeared at least once. A higher value (e.g., 1.5) will penalize repetitions more strongly, while a lower value (e.g., 0.9) will be more lenient. At 0, it is disabled.'
			)}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs">
					{'presence_penalty'}
				</div>

				<button
					class="p-1 px-3 text-xs flex rounded transition flex-shrink-0 outline-none"
					type="button"
					on:click={() => {
						params.presence_penalty = (params?.presence_penalty ?? null) === null ? 0.0 : null;
					}}
				>
					{#if (params?.presence_penalty ?? null) === null}
						<span class="ml-2 self-center">{$i18n.t('Default')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
					{/if}
				</button>
			</div>
		</Tooltip>

		{#if (params?.presence_penalty ?? null) !== null}
			{@render rangeParam('presence_penalty', 'presence_penalty', -2, 2, 0.05)}
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<Tooltip
			content={$i18n.t('Enable Mirostat sampling for controlling perplexity.')}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs">
					{'mirostat'}
				</div>
				<button
					class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
					type="button"
					on:click={() => {
						params.mirostat = (params?.mirostat ?? null) === null ? 0 : null;
					}}
				>
					{#if (params?.mirostat ?? null) === null}
						<span class="ml-2 self-center">{$i18n.t('Default')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
					{/if}
				</button>
			</div>
		</Tooltip>

		{#if (params?.mirostat ?? null) !== null}
			{@render rangeParam('mirostat', 'mirostat', 0, 2, 1, 1)}
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<Tooltip
			content={$i18n.t(
				'Influences how quickly the algorithm responds to feedback from the generated text. A lower learning rate will result in slower adjustments, while a higher learning rate will make the algorithm more responsive.'
			)}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs">
					{'mirostat_eta'}
				</div>
				<button
					class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
					type="button"
					on:click={() => {
						params.mirostat_eta = (params?.mirostat_eta ?? null) === null ? 0.1 : null;
					}}
				>
					{#if (params?.mirostat_eta ?? null) === null}
						<span class="ml-2 self-center">{$i18n.t('Default')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
					{/if}
				</button>
			</div>
		</Tooltip>

		{#if (params?.mirostat_eta ?? null) !== null}
			{@render rangeParam('mirostat_eta', 'mirostat_eta', 0, 1, 0.05)}
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<Tooltip
			content={$i18n.t(
				'Controls the balance between coherence and diversity of the output. A lower value will result in more focused and coherent text.'
			)}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs">
					{'mirostat_tau'}
				</div>

				<button
					class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
					type="button"
					on:click={() => {
						params.mirostat_tau = (params?.mirostat_tau ?? null) === null ? 5.0 : null;
					}}
				>
					{#if (params?.mirostat_tau ?? null) === null}
						<span class="ml-2 self-center">{$i18n.t('Default')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
					{/if}
				</button>
			</div>
		</Tooltip>

		{#if (params?.mirostat_tau ?? null) !== null}
			{@render rangeParam('mirostat_tau', 'mirostat_tau', 0, 10, 0.5)}
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<Tooltip
			content={$i18n.t('Sets how far back for the model to look back to prevent repetition.')}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs">
					{'repeat_last_n'}
				</div>

				<button
					class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
					type="button"
					on:click={() => {
						params.repeat_last_n = (params?.repeat_last_n ?? null) === null ? 64 : null;
					}}
				>
					{#if (params?.repeat_last_n ?? null) === null}
						<span class="ml-2 self-center">{$i18n.t('Default')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
					{/if}
				</button>
			</div>
		</Tooltip>

		{#if (params?.repeat_last_n ?? null) !== null}
			{@render rangeParam('repeat_last_n', 'repeat_last_n', -1, 128, 1, 1)}
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<Tooltip
			content={$i18n.t(
				'Tail free sampling is used to reduce the impact of less probable tokens from the output. A higher value (e.g., 2.0) will reduce the impact more, while a value of 1.0 disables this setting.'
			)}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs">
					{'tfs_z'}
				</div>

				<button
					class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
					type="button"
					on:click={() => {
						params.tfs_z = (params?.tfs_z ?? null) === null ? 1 : null;
					}}
				>
					{#if (params?.tfs_z ?? null) === null}
						<span class="ml-2 self-center">{$i18n.t('Default')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
					{/if}
				</button>
			</div>
		</Tooltip>

		{#if (params?.tfs_z ?? null) !== null}
			{@render rangeParam('tfs_z', 'tfs_z', 0, 2, 0.05)}
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<Tooltip
			content={$i18n.t(
				'Control the repetition of token sequences in the generated text. A higher value (e.g., 1.5) will penalize repetitions more strongly, while a lower value (e.g., 1.1) will be more lenient. At 1, it is disabled.'
			)}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs">
					{'repeat_penalty'}
				</div>

				<button
					class="p-1 px-3 text-xs flex rounded transition flex-shrink-0 outline-none"
					type="button"
					on:click={() => {
						params.repeat_penalty = (params?.repeat_penalty ?? null) === null ? 1.1 : null;
					}}
				>
					{#if (params?.repeat_penalty ?? null) === null}
						<span class="ml-2 self-center">{$i18n.t('Default')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
					{/if}
				</button>
			</div>
		</Tooltip>

		{#if (params?.repeat_penalty ?? null) !== null}
			{@render rangeParam('repeat_penalty', 'repeat_penalty', -2, 2, 0.05)}
		{/if}
	</div>

	{#if admin}
		<div class=" py-0.5 w-full justify-between">
			<Tooltip
				content={$i18n.t(
					'Enable Memory Mapping (mmap) to load model data. This option allows the system to use disk storage as an extension of RAM by treating disk files as if they were in RAM. This can improve model performance by allowing for faster data access. However, it may not work correctly with all systems and can consume a significant amount of disk space.'
				)}
				placement="top-start"
				className="inline-tooltip"
			>
				<div class="flex w-full justify-between">
					<div class=" self-center text-xs">
						{'use_mmap'}
					</div>
					<button
						class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
						type="button"
						on:click={() => {
							params.use_mmap = (params?.use_mmap ?? null) === null ? true : null;
						}}
					>
						{#if (params?.use_mmap ?? null) === null}
							<span class="ml-2 self-center">{$i18n.t('Default')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
						{/if}
					</button>
				</div>
			</Tooltip>

			{#if (params?.use_mmap ?? null) !== null}
				<div class="flex justify-between items-center mt-1">
					<div class="text-xs text-gray-500">
						{params.use_mmap ? $i18n.t('Enabled') : $i18n.t('Disabled')}
					</div>
					<div class=" pr-2">
						<Switch bind:state={params.use_mmap} ariaLabel="use_mmap" />
					</div>
				</div>
			{/if}
		</div>

		<div class=" py-0.5 w-full justify-between">
			<Tooltip
				content={$i18n.t(
					"Enable Memory Locking (mlock) to prevent model data from being swapped out of RAM. This option locks the model's working set of pages into RAM, ensuring that they will not be swapped out to disk. This can help maintain performance by avoiding page faults and ensuring fast data access."
				)}
				placement="top-start"
				className="inline-tooltip"
			>
				<div class="flex w-full justify-between">
					<div class=" self-center text-xs">
						{'use_mlock'}
					</div>

					<button
						class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
						type="button"
						on:click={() => {
							params.use_mlock = (params?.use_mlock ?? null) === null ? true : null;
						}}
					>
						{#if (params?.use_mlock ?? null) === null}
							<span class="ml-2 self-center">{$i18n.t('Default')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
						{/if}
					</button>
				</div>
			</Tooltip>

			{#if (params?.use_mlock ?? null) !== null}
				<div class="flex justify-between items-center mt-1">
					<div class="text-xs text-gray-500">
						{params.use_mlock ? $i18n.t('Enabled') : $i18n.t('Disabled')}
					</div>

					<div class=" pr-2">
						<Switch bind:state={params.use_mlock} ariaLabel="use_mlock" />
					</div>
				</div>
			{/if}
		</div>
	{/if}

	<div class=" py-0.5 w-full justify-between">
		<Tooltip
			content={$i18n.t(
				'This option enables or disables the use of the reasoning feature in Ollama, which allows the model to think before generating a response. When enabled, the model can take a moment to process the conversation context and generate a more thoughtful response.'
			)}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class=" py-0.5 flex w-full justify-between">
				<div class=" self-center text-xs">
					{'think'} ({$i18n.t('Ollama')})
				</div>
				<button
					class="p-1 px-3 text-xs flex rounded-sm transition"
					on:click={() => {
						if ((params?.think ?? null) === null) {
							params.think = true;
						} else if (params.think === true) {
							params.think = 'medium';
						} else if (typeof params.think === 'string') {
							params.think = false;
						} else {
							params.think = null;
						}
					}}
					type="button"
				>
					{#if params.think === true}
						<span class="ml-2 self-center">{$i18n.t('On')}</span>
					{:else if params.think === false}
						<span class="ml-2 self-center">{$i18n.t('Off')}</span>
					{:else if typeof params.think === 'string'}
						<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Default')}</span>
					{/if}
				</button>
			</div>
		</Tooltip>

		{#if typeof params.think === 'string'}
			<div class="flex mt-0.5 space-x-2">
				<div class=" flex-1">
					<input
						class="text-sm w-full bg-transparent outline-hidden outline-none"
						type="text"
						aria-label={`think (${$i18n.t('Ollama')})`}
						placeholder={$i18n.t("e.g. 'low', 'medium', 'high'")}
						bind:value={params.think}
						autocomplete="off"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<Tooltip
			content={$i18n.t('The format to return a response in. Format can be json or a JSON schema.')}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class=" py-0.5 flex w-full justify-between">
				<div class=" self-center text-xs">
					{'format'} ({$i18n.t('Ollama')})
				</div>
				<button
					class="p-1 px-3 text-xs flex rounded-sm transition"
					on:click={() => {
						params.format = (params?.format ?? null) === null ? 'json' : null;
					}}
					type="button"
				>
					{#if (params?.format ?? null) === null}
						<span class="ml-2 self-center">{$i18n.t('Default')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('JSON')}</span>
					{/if}
				</button>
			</div>
		</Tooltip>

		{#if (params?.format ?? null) !== null}
			<div class="flex mt-0.5 space-x-2">
				<Textarea
					className="w-full  text-sm bg-transparent outline-hidden"
					ariaLabel={`format (${$i18n.t('Ollama')})`}
					placeholder={$i18n.t('e.g. "json" or a JSON schema')}
					bind:value={params.format}
				/>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<Tooltip
			content={$i18n.t(
				'This option controls how many tokens are preserved when refreshing the context. For example, if set to 2, the last 2 tokens of the conversation context will be retained. Preserving context can help maintain the continuity of a conversation, but it may reduce the ability to respond to new topics.'
			)}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs">
					{'num_keep'} ({$i18n.t('Ollama')})
				</div>

				<button
					class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
					type="button"
					on:click={() => {
						params.num_keep = (params?.num_keep ?? null) === null ? 24 : null;
					}}
				>
					{#if (params?.num_keep ?? null) === null}
						<span class="ml-2 self-center">{$i18n.t('Default')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
					{/if}
				</button>
			</div>
		</Tooltip>

		{#if (params?.num_keep ?? null) !== null}
			{@render rangeParam(
				'num_keep',
				`num_keep (${$i18n.t('Ollama')})`,
				-1,
				10240000,
				1,
				1,
				undefined
			)}
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<Tooltip
			content={$i18n.t('Sets the size of the context window used to generate the next token.')}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs">
					{'num_ctx'} ({$i18n.t('Ollama')})
				</div>

				<button
					class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
					type="button"
					on:click={() => {
						params.num_ctx = (params?.num_ctx ?? null) === null ? 2048 : null;
					}}
				>
					{#if (params?.num_ctx ?? null) === null}
						<span class="ml-2 self-center">{$i18n.t('Default')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
					{/if}
				</button>
			</div>
		</Tooltip>

		{#if (params?.num_ctx ?? null) !== null}
			{@render rangeParam(
				'num_ctx',
				`num_ctx (${$i18n.t('Ollama')})`,
				-1,
				10240000,
				1,
				1,
				undefined
			)}
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<Tooltip
			content={$i18n.t(
				'The batch size determines how many text requests are processed together at once. A higher batch size can increase the performance and speed of the model, but it also requires more memory.'
			)}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs">
					{'num_batch'} ({$i18n.t('Ollama')})
				</div>

				<button
					class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
					type="button"
					on:click={() => {
						params.num_batch = (params?.num_batch ?? null) === null ? 512 : null;
					}}
				>
					{#if (params?.num_batch ?? null) === null}
						<span class="ml-2 self-center">{$i18n.t('Default')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
					{/if}
				</button>
			</div>
		</Tooltip>

		{#if (params?.num_batch ?? null) !== null}
			{@render rangeParam(
				'num_batch',
				`num_batch (${$i18n.t('Ollama')})`,
				256,
				8192,
				256,
				256,
				undefined
			)}
		{/if}
	</div>

	{#if admin}
		<div class=" py-0.5 w-full justify-between">
			<Tooltip
				content={$i18n.t(
					'Set the number of worker threads used for computation. This option controls how many threads are used to process incoming requests concurrently. Increasing this value can improve performance under high concurrency workloads but may also consume more CPU resources.'
				)}
				placement="top-start"
				className="inline-tooltip"
			>
				<div class="flex w-full justify-between">
					<div class=" self-center text-xs">
						{'num_thread'} ({$i18n.t('Ollama')})
					</div>

					<button
						class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
						type="button"
						on:click={() => {
							params.num_thread = (params?.num_thread ?? null) === null ? 2 : null;
						}}
					>
						{#if (params?.num_thread ?? null) === null}
							<span class="ml-2 self-center">{$i18n.t('Default')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
						{/if}
					</button>
				</div>
			</Tooltip>

			{#if (params?.num_thread ?? null) !== null}
				{@render rangeParam('num_thread', `num_thread (${$i18n.t('Ollama')})`, 1, 256, 1, 1)}
			{/if}
		</div>

		<div class=" py-0.5 w-full justify-between">
			<Tooltip
				content={$i18n.t(
					'Set the number of layers, which will be off-loaded to GPU. Increasing this value can significantly improve performance for models that are optimized for GPU acceleration but may also consume more power and GPU resources.'
				)}
				placement="top-start"
				className="inline-tooltip"
			>
				<div class="flex w-full justify-between">
					<div class=" self-center text-xs">
						{'num_gpu'} ({$i18n.t('Ollama')})
					</div>

					<button
						class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
						type="button"
						on:click={() => {
							params.num_gpu = (params?.num_gpu ?? null) === null ? 0 : null;
						}}
					>
						{#if (params?.num_gpu ?? null) === null}
							<span class="ml-2 self-center">{$i18n.t('Default')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
						{/if}
					</button>
				</div>
			</Tooltip>

			{#if (params?.num_gpu ?? null) !== null}
				{@render rangeParam('num_gpu', `num_gpu (${$i18n.t('Ollama')})`, 0, 256, 1, 1)}
			{/if}
		</div>

		<div class=" py-0.5 w-full justify-between">
			<Tooltip
				content={$i18n.t(
					'This option controls how long the model will stay loaded into memory following the request (default: 5m)'
				)}
				placement="top-start"
				className="inline-tooltip"
			>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">
						{'keep_alive'} ({$i18n.t('Ollama')})
					</div>
					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							params.keep_alive = (params?.keep_alive ?? null) === null ? '5m' : null;
						}}
						type="button"
					>
						{#if (params?.keep_alive ?? null) === null}
							<span class="ml-2 self-center">{$i18n.t('Default')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
						{/if}
					</button>
				</div>
			</Tooltip>

			{#if (params?.keep_alive ?? null) !== null}
				<div class="flex mt-0.5 space-x-2">
					<input
						class="w-full text-sm bg-transparent outline-hidden"
						type="text"
						aria-label={`keep_alive (${$i18n.t('Ollama')})`}
						placeholder={$i18n.t("e.g. '30s','10m'. Valid time units are 's', 'm', 'h'.")}
						bind:value={params.keep_alive}
					/>
				</div>
			{/if}
		</div>

		{#if custom && admin}
			<div class="flex flex-col justify-center">
				{#each Object.keys(params?.custom_params ?? {}) as key}
					<div class=" py-0.5 w-full justify-between mb-1">
						<div class="flex w-full justify-between">
							<div class=" self-center text-xs">
								<input
									type="text"
									class=" text-xs w-full bg-transparent outline-none"
									aria-label={$i18n.t('Custom Parameter Name')}
									placeholder={$i18n.t('Custom Parameter Name')}
									value={key}
									on:change={(e) => {
										const newKey = e.currentTarget.value.trim();
										if (newKey && newKey !== key) {
											params.custom_params[newKey] = params.custom_params[key];
											delete params.custom_params[key];
											params = {
												...params,
												custom_params: { ...params.custom_params }
											};
										}
									}}
								/>
							</div>
							<button
								class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
								type="button"
								on:click={() => {
									delete params.custom_params[key];
									params = {
										...params,
										custom_params: { ...params.custom_params }
									};
								}}
							>
								{$i18n.t('Remove')}
							</button>
						</div>
						<div class="flex mt-0.5 space-x-2">
							<div class=" flex-1">
								<input
									bind:value={params.custom_params[key]}
									type="text"
									class="text-sm w-full bg-transparent outline-hidden outline-none"
									aria-label={$i18n.t('Custom Parameter Value')}
									placeholder={$i18n.t('Custom Parameter Value')}
								/>
							</div>
						</div>
					</div>
				{/each}

				<button
					class=" flex gap-2 items-center w-full text-center justify-center mt-1 mb-5"
					type="button"
					on:click={() => {
						params.custom_params = (params?.custom_params ?? {}) || {};
						params.custom_params['custom_param_name'] = 'custom_param_value';
					}}
				>
					<div>
						<Plus />
					</div>
					<div>{$i18n.t('Add Custom Parameter')}</div>
				</button>
			</div>
		{/if}
	{/if}
</div>
