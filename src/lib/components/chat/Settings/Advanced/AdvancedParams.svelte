<script lang="ts">
  import { run } from 'svelte/legacy';

  import Switch from '$lib/components/common/Switch.svelte';
  import Tooltip from '$lib/components/common/Tooltip.svelte';
  import { getContext, createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher();

  const i18n = getContext('i18n');


  interface Props {
    admin?: boolean;
    params?: any;
  }

  let { admin = false, params = $bindable({
    // Advanced
    stream_response: null, // Set stream responses for this model individually
    function_calling: null,
    seed: null,
    stop: null,
    temperature: null,
    reasoning_effort: null,
    frequency_penalty: null,
    repeat_last_n: null,
    mirostat: null,
    mirostat_eta: null,
    mirostat_tau: null,
    top_k: null,
    top_p: null,
    min_p: null,
    tfs_z: null,
    num_ctx: null,
    num_batch: null,
    num_keep: null,
    max_tokens: null,
    use_mmap: null,
    use_mlock: null,
    num_thread: null,
    num_gpu: null,
    template: null
  }) }: Props = $props();

  let customFieldName = '';
  let customFieldValue = '';

  run(() => {
    if (params) {
      dispatch('change', params);
    }
  });
</script>

<div class=" space-y-1 text-xs pb-safe-bottom">
  <div>
    <Tooltip
      className="inline-tooltip"
      content={$i18n.t(
        'When enabled, the model will respond to each chat message in real-time, generating a response as soon as the user sends a message. This mode is useful for live chat applications, but may impact performance on slower hardware.'
      )}
      placement="top-start"
    >
      <div class=" py-0.5 flex w-full justify-between">
        <div class=" self-center text-xs font-medium">
          {$i18n.t('Stream Chat Response')}
        </div>
        <button
          class="p-1 px-3 text-xs flex rounded-sm transition"
          type="button"
          onclick={() => {
            params.stream_response =
              (params?.stream_response ?? null) === null
                ? true
                : params.stream_response
                ? false
                : null;
          }}
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

  <div>
    <Tooltip
      className="inline-tooltip"
      content={$i18n.t(
        'Default mode works with a wider range of models by calling tools once before execution. Native mode leverages the model’s built-in tool-calling capabilities, but requires the model to inherently support this feature.'
      )}
      placement="top-start"
    >
      <div class=" py-0.5 flex w-full justify-between">
        <div class=" self-center text-xs font-medium">
          {$i18n.t('Function Calling')}
        </div>
        <button
          class="p-1 px-3 text-xs flex rounded-sm transition"
          type="button"
          onclick={() => {
            params.function_calling = (params?.function_calling ?? null) === null ? 'native' : null;
          }}
        >
          {#if params.function_calling === 'native'}
            <span class="ml-2 self-center">{$i18n.t('Native')}</span>
          {:else}
            <span class="ml-2 self-center">{$i18n.t('Default')}</span>
          {/if}
        </button>
      </div>
    </Tooltip>
  </div>

  <div class=" py-0.5 w-full justify-between">
    <Tooltip
      className="inline-tooltip"
      content={$i18n.t(
				'Sets the random number seed to use for generation. Setting this to a specific number will make the model generate the same text for the same prompt.'
        )}
      placement="top-start"
    >
      <div class="flex w-full justify-between">
        <div class=" self-center text-xs font-medium">
          {$i18n.t('Seed')}
        </div>

        <button
          class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
          type="button"
          onclick={() => {
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
            class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden"
            autocomplete="off"
            min="0"
            placeholder={$i18n.t('Enter Seed')}
            type="number"
            bind:value={params.seed}
          />
        </div>
      </div>
    {/if}
  </div>

  <div class=" py-0.5 w-full justify-between">
    <Tooltip
      className="inline-tooltip"
      content={$i18n.t(
        'Sets the stop sequences to use. When this pattern is encountered, the LLM will stop generating text and return. Multiple stop patterns may be set by specifying multiple separate stop parameters in a modelfile.'
      )}
      placement="top-start"
    >
      <div class="flex w-full justify-between">
        <div class=" self-center text-xs font-medium">
          {$i18n.t('Stop Sequence')}
        </div>

        <button
          class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
          type="button"
          onclick={() => {
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
            class="w-full rounded-lg py-2 px-1 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden"
            autocomplete="off"
            placeholder={$i18n.t('Enter stop sequence')}
            type="text"
            bind:value={params.stop}
          />
        </div>
      </div>
    {/if}
  </div>

  <div class=" py-0.5 w-full justify-between">
    <Tooltip
      className="inline-tooltip"
      content={$i18n.t(
				'The temperature of the model. Increasing the temperature will make the model answer more creatively.'
        )}
      placement="top-start"
    >
      <div class="flex w-full justify-between">
        <div class=" self-center text-xs font-medium">
          {$i18n.t('Temperature')}
        </div>
        <button
          class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
          type="button"
          onclick={() => {
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
      <div class="flex mt-0.5 space-x-2">
        <div class=" flex-1">
          <input
            id="steps-range"
            class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
            max="2"
            min="0"
            step="0.05"
            type="range"
            bind:value={params.temperature}
          />
        </div>
        <div>
          <input
            class=" bg-transparent text-center w-14"
            max="2"
            min="0"
            step="any"
            type="number"
            bind:value={params.temperature}
          />
        </div>
      </div>
    {/if}
  </div>

  <div class=" py-0.5 w-full justify-between">
    <Tooltip
      className="inline-tooltip"
      content={$i18n.t(
				'Constrains effort on reasoning for reasoning models. Only applicable to reasoning models from specific providers that support reasoning effort.'
        )}
      placement="top-start"
    >
      <div class="flex w-full justify-between">
        <div class=" self-center text-xs font-medium">
          {$i18n.t('Reasoning Effort')}
        </div>
        <button
          class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
          type="button"
          onclick={() => {
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
            class="w-full rounded-lg py-2 px-1 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden"
            autocomplete="off"
            placeholder={$i18n.t('Enter reasoning effort')}
            type="text"
            bind:value={params.reasoning_effort}
          />
        </div>
      </div>
    {/if}
  </div>

  <div class=" py-0.5 w-full justify-between">
    <Tooltip
      className="inline-tooltip"
			content={$i18n.t('Enable Mirostat sampling for controlling perplexity.')}
      placement="top-start"
    >
      <div class="flex w-full justify-between">
        <div class=" self-center text-xs font-medium">
          {$i18n.t('Mirostat')}
        </div>
        <button
          class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
          type="button"
          onclick={() => {
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
      <div class="flex mt-0.5 space-x-2">
        <div class=" flex-1">
          <input
            id="steps-range"
            class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
            max="2"
            min="0"
            step="1"
            type="range"
            bind:value={params.mirostat}
          />
        </div>
        <div>
          <input
            class=" bg-transparent text-center w-14"
            max="2"
            min="0"
            step="1"
            type="number"
            bind:value={params.mirostat}
          />
        </div>
      </div>
    {/if}
  </div>

  <div class=" py-0.5 w-full justify-between">
    <Tooltip
      className="inline-tooltip"
      content={$i18n.t(
				'Influences how quickly the algorithm responds to feedback from the generated text. A lower learning rate will result in slower adjustments, while a higher learning rate will make the algorithm more responsive.'
        )}
      placement="top-start"
    >
      <div class="flex w-full justify-between">
        <div class=" self-center text-xs font-medium">
          {$i18n.t('Mirostat Eta')}
        </div>
        <button
          class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
          type="button"
          onclick={() => {
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
      <div class="flex mt-0.5 space-x-2">
        <div class=" flex-1">
          <input
            id="steps-range"
            class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
            max="1"
            min="0"
            step="0.05"
            type="range"
            bind:value={params.mirostat_eta}
          />
        </div>
        <div>
          <input
            class=" bg-transparent text-center w-14"
            max="1"
            min="0"
            step="any"
            type="number"
            bind:value={params.mirostat_eta}
          />
        </div>
      </div>
    {/if}
  </div>

	<div class=" py-0.5 w-full justify-between">
		<Tooltip
			content={$i18n.t(
        'Controls the balance between coherence and diversity of the output. A lower value will result in more focused and coherent text. (Default: 5.0)'
      )}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Mirostat Tau')}
				</div>

        <button
          class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
          type="button"
          onclick={() => {
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
      <div class="flex mt-0.5 space-x-2">
        <div class=" flex-1">
          <input
            id="steps-range"
            class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
            max="10"
            min="0"
            step="0.5"
            type="range"
            bind:value={params.mirostat_tau}
          />
        </div>
        <div>
          <input
            class=" bg-transparent text-center w-14"
            max="10"
            min="0"
            step="any"
            type="number"
            bind:value={params.mirostat_tau}
          />
        </div>
      </div>
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
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Top K')}
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
            id="steps-range"
            class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
            max="1000"
            min="0"
            step="0.5"
            type="range"
            bind:value={params.top_k}
          />
        </div>
        <div>
          <input
            class=" bg-transparent text-center w-14"
            max="100"
            min="0"
            step="any"
            type="number"
            bind:value={params.top_k}
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
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Top P')}
				</div>

        <button
          class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
          type="button"
          onclick={() => {
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
      <div class="flex mt-0.5 space-x-2">
        <div class=" flex-1">
          <input
            id="steps-range"
            class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
            max="1"
            min="0"
            step="0.05"
            type="range"
            bind:value={params.top_p}
          />
        </div>
        <div>
          <input
            class=" bg-transparent text-center w-14"
            max="1"
            min="0"
            step="any"
            type="number"
            bind:value={params.top_p}
          />
        </div>
      </div>
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
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Min P')}
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
      <div class="flex mt-0.5 space-x-2">
        <div class=" flex-1">
          <input
            id="steps-range"
            class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
            max="1"
            min="0"
            step="0.05"
            type="range"
            bind:value={params.min_p}
          />
        </div>
        <div>
          <input
            class=" bg-transparent text-center w-14"
            max="1"
            min="0"
            step="any"
            type="number"
            bind:value={params.min_p}
          />
        </div>
      </div>
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
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Frequency Penalty')}
				</div>

        <button
          class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
          type="button"
          onclick={() => {
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
      <div class="flex mt-0.5 space-x-2">
        <div class=" flex-1">
          <input
            id="steps-range"
            class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
            max="2"
            min="-2"
            step="0.05"
            type="range"
            bind:value={params.frequency_penalty}
          />
        </div>
        <div>
          <input
            class=" bg-transparent text-center w-14"
            max="2"
            min="-2"
            step="any"
            type="number"
            bind:value={params.frequency_penalty}
          />
        </div>
      </div>
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
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Presence Penalty')}
				</div>

        <button
          class="p-1 px-3 text-xs flex rounded transition flex-shrink-0 outline-none"
          type="button"
          onclick={() => {
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
      <div class="flex mt-0.5 space-x-2">
        <div class=" flex-1">
          <input
            id="steps-range"
            class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
            max="2"
            min="-2"
            step="0.05"
            type="range"
            bind:value={params.presence_penalty}
          />
        </div>
        <div>
          <input
            class=" bg-transparent text-center w-14"
            max="2"
            min="-2"
            step="any"
            type="number"
            bind:value={params.presence_penalty}
          />
        </div>
      </div>
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
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Repeat Penalty (Ollama)')}
				</div>

        <button
          class="p-1 px-3 text-xs flex rounded transition flex-shrink-0 outline-none"
          type="button"
          onclick={() => {
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
      <div class="flex mt-0.5 space-x-2">
        <div class=" flex-1">
          <input
            id="steps-range"
            class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
            max="2"
            min="-2"
            step="0.05"
            type="range"
            bind:value={params.repeat_penalty}
          />
        </div>
        <div>
          <input
            class=" bg-transparent text-center w-14"
            max="2"
            min="-2"
            step="any"
            type="number"
            bind:value={params.repeat_penalty}
          />
        </div>
      </div>
    {/if}
  </div>

	<div class=" py-0.5 w-full justify-between">
		<Tooltip
    content={$i18n.t('Sets how far back for the model to look back to prevent repetition.')}

			placement="top-start"
			className="inline-tooltip"
		>
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Repeat Last N')}
				</div>

        <button
          class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
          type="button"
          onclick={() => {
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
      <div class="flex mt-0.5 space-x-2">
        <div class=" flex-1">
          <input
            id="steps-range"
            class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
            max="128"
            min="-1"
            step="1"
            type="range"
            bind:value={params.repeat_last_n}
          />
        </div>
        <div>
          <input
            class=" bg-transparent text-center w-14"
            max="128"
            min="-1"
            step="1"
            type="number"
            bind:value={params.repeat_last_n}
          />
        </div>
      </div>
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
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Tfs Z')}
				</div>

        <button
          class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
          type="button"
          onclick={() => {
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
      <div class="flex mt-0.5 space-x-2">
        <div class=" flex-1">
          <input
            id="steps-range"
            class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
            max="2"
            min="0"
            step="0.05"
            type="range"
            bind:value={params.tfs_z}
          />
        </div>
        <div>
          <input
            class=" bg-transparent text-center w-14"
            max="2"
            min="0"
            step="any"
            type="number"
            bind:value={params.tfs_z}
          />
        </div>
      </div>
    {/if}
  </div>

	<div class=" py-0.5 w-full justify-between">
		<Tooltip
    content={$i18n.t('Sets the size of the context window used to generate the next token.')}

			placement="top-start"
			className="inline-tooltip"
		>
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Context Length')}
				</div>

        <button
          class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
          type="button"
          onclick={() => {
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
      <div class="flex mt-0.5 space-x-2">
        <div class=" flex-1">
          <input
            id="steps-range"
            class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
            max="10240000"
            min="-1"
            step="1"
            type="range"
            bind:value={params.num_ctx}
          />
        </div>
        <div class="">
          <input
            class=" bg-transparent text-center w-14"
            min="-1"
            step="1"
            type="number"
            bind:value={params.num_ctx}
          />
        </div>
      </div>
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
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Batch Size (num_batch)')}
				</div>

        <button
          class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
          type="button"
          onclick={() => {
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
      <div class="flex mt-0.5 space-x-2">
        <div class=" flex-1">
          <input
            id="steps-range"
            class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
            max="8192"
            min="256"
            step="256"
            type="range"
            bind:value={params.num_batch}
          />
        </div>
        <div>
          <input
            class=" bg-transparent text-center w-14"
            min="256"
            step="256"
            type="number"
            bind:value={params.num_batch}
          />
        </div>
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
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Tokens To Keep On Context Refresh (num_keep)')}
				</div>

        <button
          class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
          type="button"
          onclick={() => {
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
      <div class="flex mt-0.5 space-x-2">
        <div class=" flex-1">
          <input
            id="steps-range"
            class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
            max="10240000"
            min="-1"
            step="1"
            type="range"
            bind:value={params.num_keep}
          />
        </div>
        <div class="">
          <input
            class=" bg-transparent text-center w-14"
            min="-1"
            step="1"
            type="number"
            bind:value={params.num_keep}
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
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Max Tokens (num_predict)')}
				</div>

        <button
          class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
          type="button"
          onclick={() => {
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
      <div class="flex mt-0.5 space-x-2">
        <div class=" flex-1">
          <input
            id="steps-range"
            class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
            max="131072"
            min="-2"
            step="1"
            type="range"
            bind:value={params.max_tokens}
          />
        </div>
        <div>
          <input
            class=" bg-transparent text-center w-14"
            min="-2"
            step="1"
            type="number"
            bind:value={params.max_tokens}
          />
        </div>
      </div>
    {/if}
  </div>

  {#if admin}
    <div class=" py-0.5 w-full justify-between">
      <Tooltip
        className="inline-tooltip"
        content={$i18n.t(
          'Enable Memory Mapping (mmap) to load model data. This option allows the system to use disk storage as an extension of RAM by treating disk files as if they were in RAM. This can improve model performance by allowing for faster data access. However, it may not work correctly with all systems and can consume a significant amount of disk space.'
        )}
        placement="top-start"
      >
        <div class="flex w-full justify-between">
          <div class=" self-center text-xs font-medium">
            {$i18n.t('use_mmap (Ollama)')}
          </div>
          <button
            class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
            type="button"
            onclick={() => {
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
            {params.use_mmap ? 'Enabled' : 'Disabled'}
          </div>
          <div class=" pr-2">
            <Switch bind:state={params.use_mmap} />
          </div>
        </div>
      {/if}
    </div>

    <div class=" py-0.5 w-full justify-between">
      <Tooltip
        className="inline-tooltip"
        content={$i18n.t(
          "Enable Memory Locking (mlock) to prevent model data from being swapped out of RAM. This option locks the model's working set of pages into RAM, ensuring that they will not be swapped out to disk. This can help maintain performance by avoiding page faults and ensuring fast data access."
        )}
        placement="top-start"
      >
        <div class="flex w-full justify-between">
          <div class=" self-center text-xs font-medium">
            {$i18n.t('use_mlock (Ollama)')}
          </div>

          <button
            class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
            type="button"
            onclick={() => {
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
            {params.use_mlock ? 'Enabled' : 'Disabled'}
          </div>

          <div class=" pr-2">
            <Switch bind:state={params.use_mlock} />
          </div>
        </div>
      {/if}
    </div>

    <div class=" py-0.5 w-full justify-between">
      <Tooltip
        className="inline-tooltip"
        content={$i18n.t(
          'Set the number of worker threads used for computation. This option controls how many threads are used to process incoming requests concurrently. Increasing this value can improve performance under high concurrency workloads but may also consume more CPU resources.'
        )}
        placement="top-start"
      >
        <div class="flex w-full justify-between">
          <div class=" self-center text-xs font-medium">
            {$i18n.t('num_thread (Ollama)')}
          </div>

          <button
            class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
            type="button"
            onclick={() => {
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
        <div class="flex mt-0.5 space-x-2">
          <div class=" flex-1">
            <input
              id="steps-range"
              class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
              max="256"
              min="1"
              step="1"
              type="range"
              bind:value={params.num_thread}
            />
          </div>
          <div class="">
            <input
              class=" bg-transparent text-center w-14"
              max="256"
              min="1"
              step="1"
              type="number"
              bind:value={params.num_thread}
            />
          </div>
        </div>
      {/if}
    </div>

    <div class=" py-0.5 w-full justify-between">
      <Tooltip
        className="inline-tooltip"
        content={$i18n.t(
          'Set the number of layers, which will be off-loaded to GPU. Increasing this value can significantly improve performance for models that are optimized for GPU acceleration but may also consume more power and GPU resources.'
        )}
        placement="top-start"
      >
        <div class="flex w-full justify-between">
          <div class=" self-center text-xs font-medium">
            {$i18n.t('num_gpu (Ollama)')}
          </div>

          <button
            class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
            type="button"
            onclick={() => {
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
        <div class="flex mt-0.5 space-x-2">
          <div class=" flex-1">
            <input
              id="steps-range"
              class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
              max="256"
              min="0"
              step="1"
              type="range"
              bind:value={params.num_gpu}
            />
          </div>
          <div class="">
            <input
              class=" bg-transparent text-center w-14"
              max="256"
              min="0"
              step="1"
              type="number"
              bind:value={params.num_gpu}
            />
          </div>
        </div>
      {/if}
    </div>

    <!-- <div class=" py-0.5 w-full justify-between">
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs font-medium">{$i18n.t('Template')}</div>

				<button
					class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
					type="button"
					on:click={() => {
						params.template = (params?.template ?? null) === null ? '' : null;
					}}
				>
					{#if (params?.template ?? null) === null}
						<span class="ml-2 self-center">{$i18n.t('Default')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
					{/if}
				</button>
			</div>

			{#if (params?.template ?? null) !== null}
				<div class="flex mt-0.5 space-x-2">
					<div class=" flex-1">
						<textarea
							class="px-3 py-1.5 text-sm w-full bg-transparent border dark:border-gray-600 outline-hidden rounded-lg -mb-1"
							placeholder={$i18n.t('Write your model template content here')}
							rows="4"
							bind:value={params.template}
						/>
					</div>
				</div>
			{/if}
		</div> -->
  {/if}
</div>
