<script lang="ts">
	import Switch from '$lib/components/common/Switch.svelte';
	import { getContext, createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	export let admin = false;

	export let params = {
		// Advanced
		stream_response: null, // Set stream responses for this model individually
		seed: null,
		stop: null,
		temperature: null,
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
	};

	let customFieldName = '';
	let customFieldValue = '';

	$: if (params) {
		dispatch('change', params);
	}
</script>

<div class=" space-y-1 text-xs pb-safe-bottom">
	<div>
		<div class=" py-0.5 flex w-full justify-between">
			<div class=" self-center text-xs font-medium">
				{$i18n.t('Stream Chat Response')}
			</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition"
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
	</div>

	<div class=" py-0.5 w-full justify-between">
		<div class="flex w-full justify-between">
			<div class=" self-center text-xs font-medium">{$i18n.t('Seed')}</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition flex-shrink-0 outline-none"
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

		{#if (params?.seed ?? null) !== null}
			<div class="flex mt-0.5 space-x-2">
				<div class=" flex-1">
					<input
						class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
						type="number"
						placeholder="Enter Seed"
						bind:value={params.seed}
						autocomplete="off"
						min="0"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<div class="flex w-full justify-between">
			<div class=" self-center text-xs font-medium">{$i18n.t('Stop Sequence')}</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition flex-shrink-0 outline-none"
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

		{#if (params?.stop ?? null) !== null}
			<div class="flex mt-0.5 space-x-2">
				<div class=" flex-1">
					<input
						class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
						type="text"
						placeholder={$i18n.t('Enter stop sequence')}
						bind:value={params.stop}
						autocomplete="off"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<div class="flex w-full justify-between">
			<div class=" self-center text-xs font-medium">{$i18n.t('Temperature')}</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition flex-shrink-0 outline-none"
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

		{#if (params?.temperature ?? null) !== null}
			<div class="flex mt-0.5 space-x-2">
				<div class=" flex-1">
					<input
						id="steps-range"
						type="range"
						min="0"
						max="1"
						step="0.05"
						bind:value={params.temperature}
						class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
					/>
				</div>
				<div>
					<input
						bind:value={params.temperature}
						type="number"
						class=" bg-transparent text-center w-14"
						min="0"
						max="1"
						step="any"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<div class="flex w-full justify-between">
			<div class=" self-center text-xs font-medium">{$i18n.t('Mirostat')}</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition flex-shrink-0 outline-none"
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

		{#if (params?.mirostat ?? null) !== null}
			<div class="flex mt-0.5 space-x-2">
				<div class=" flex-1">
					<input
						id="steps-range"
						type="range"
						min="0"
						max="2"
						step="1"
						bind:value={params.mirostat}
						class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
					/>
				</div>
				<div>
					<input
						bind:value={params.mirostat}
						type="number"
						class=" bg-transparent text-center w-14"
						min="0"
						max="2"
						step="1"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<div class="flex w-full justify-between">
			<div class=" self-center text-xs font-medium">{$i18n.t('Mirostat Eta')}</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition flex-shrink-0 outline-none"
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

		{#if (params?.mirostat_eta ?? null) !== null}
			<div class="flex mt-0.5 space-x-2">
				<div class=" flex-1">
					<input
						id="steps-range"
						type="range"
						min="0"
						max="1"
						step="0.05"
						bind:value={params.mirostat_eta}
						class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
					/>
				</div>
				<div>
					<input
						bind:value={params.mirostat_eta}
						type="number"
						class=" bg-transparent text-center w-14"
						min="0"
						max="1"
						step="any"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<div class="flex w-full justify-between">
			<div class=" self-center text-xs font-medium">{$i18n.t('Mirostat Tau')}</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition flex-shrink-0 outline-none"
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

		{#if (params?.mirostat_tau ?? null) !== null}
			<div class="flex mt-0.5 space-x-2">
				<div class=" flex-1">
					<input
						id="steps-range"
						type="range"
						min="0"
						max="10"
						step="0.5"
						bind:value={params.mirostat_tau}
						class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
					/>
				</div>
				<div>
					<input
						bind:value={params.mirostat_tau}
						type="number"
						class=" bg-transparent text-center w-14"
						min="0"
						max="10"
						step="any"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<div class="flex w-full justify-between">
			<div class=" self-center text-xs font-medium">{$i18n.t('Top K')}</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition flex-shrink-0 outline-none"
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

		{#if (params?.top_k ?? null) !== null}
			<div class="flex mt-0.5 space-x-2">
				<div class=" flex-1">
					<input
						id="steps-range"
						type="range"
						min="0"
						max="100"
						step="0.5"
						bind:value={params.top_k}
						class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
					/>
				</div>
				<div>
					<input
						bind:value={params.top_k}
						type="number"
						class=" bg-transparent text-center w-14"
						min="0"
						max="100"
						step="any"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<div class="flex w-full justify-between">
			<div class=" self-center text-xs font-medium">{$i18n.t('Top P')}</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition flex-shrink-0 outline-none"
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

		{#if (params?.top_p ?? null) !== null}
			<div class="flex mt-0.5 space-x-2">
				<div class=" flex-1">
					<input
						id="steps-range"
						type="range"
						min="0"
						max="1"
						step="0.05"
						bind:value={params.top_p}
						class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
					/>
				</div>
				<div>
					<input
						bind:value={params.top_p}
						type="number"
						class=" bg-transparent text-center w-14"
						min="0"
						max="1"
						step="any"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<div class="flex w-full justify-between">
			<div class=" self-center text-xs font-medium">{$i18n.t('Min P')}</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition flex-shrink-0 outline-none"
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

		{#if (params?.min_p ?? null) !== null}
			<div class="flex mt-0.5 space-x-2">
				<div class=" flex-1">
					<input
						id="steps-range"
						type="range"
						min="0"
						max="1"
						step="0.05"
						bind:value={params.min_p}
						class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
					/>
				</div>
				<div>
					<input
						bind:value={params.min_p}
						type="number"
						class=" bg-transparent text-center w-14"
						min="0"
						max="1"
						step="any"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<div class="flex w-full justify-between">
			<div class=" self-center text-xs font-medium">{$i18n.t('Frequency Penalty')}</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition flex-shrink-0 outline-none"
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

		{#if (params?.frequency_penalty ?? null) !== null}
			<div class="flex mt-0.5 space-x-2">
				<div class=" flex-1">
					<input
						id="steps-range"
						type="range"
						min="0"
						max="2"
						step="0.05"
						bind:value={params.frequency_penalty}
						class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
					/>
				</div>
				<div>
					<input
						bind:value={params.frequency_penalty}
						type="number"
						class=" bg-transparent text-center w-14"
						min="0"
						max="2"
						step="any"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<div class="flex w-full justify-between">
			<div class=" self-center text-xs font-medium">{$i18n.t('Repeat Last N')}</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition flex-shrink-0 outline-none"
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

		{#if (params?.repeat_last_n ?? null) !== null}
			<div class="flex mt-0.5 space-x-2">
				<div class=" flex-1">
					<input
						id="steps-range"
						type="range"
						min="-1"
						max="128"
						step="1"
						bind:value={params.repeat_last_n}
						class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
					/>
				</div>
				<div>
					<input
						bind:value={params.repeat_last_n}
						type="number"
						class=" bg-transparent text-center w-14"
						min="-1"
						max="128"
						step="1"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<div class="flex w-full justify-between">
			<div class=" self-center text-xs font-medium">{$i18n.t('Tfs Z')}</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition flex-shrink-0 outline-none"
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

		{#if (params?.tfs_z ?? null) !== null}
			<div class="flex mt-0.5 space-x-2">
				<div class=" flex-1">
					<input
						id="steps-range"
						type="range"
						min="0"
						max="2"
						step="0.05"
						bind:value={params.tfs_z}
						class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
					/>
				</div>
				<div>
					<input
						bind:value={params.tfs_z}
						type="number"
						class=" bg-transparent text-center w-14"
						min="0"
						max="2"
						step="any"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<div class="flex w-full justify-between">
			<div class=" self-center text-xs font-medium">{$i18n.t('Context Length')}</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition flex-shrink-0 outline-none"
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

		{#if (params?.num_ctx ?? null) !== null}
			<div class="flex mt-0.5 space-x-2">
				<div class=" flex-1">
					<input
						id="steps-range"
						type="range"
						min="-1"
						max="10240000"
						step="1"
						bind:value={params.num_ctx}
						class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
					/>
				</div>
				<div class="">
					<input
						bind:value={params.num_ctx}
						type="number"
						class=" bg-transparent text-center w-14"
						min="-1"
						step="1"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<div class="flex w-full justify-between">
			<div class=" self-center text-xs font-medium">{$i18n.t('Batch Size (num_batch)')}</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition flex-shrink-0 outline-none"
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

		{#if (params?.num_batch ?? null) !== null}
			<div class="flex mt-0.5 space-x-2">
				<div class=" flex-1">
					<input
						id="steps-range"
						type="range"
						min="256"
						max="8192"
						step="256"
						bind:value={params.num_batch}
						class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
					/>
				</div>
				<div class="">
					<input
						bind:value={params.num_batch}
						type="number"
						class=" bg-transparent text-center w-14"
						min="256"
						step="256"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<div class="flex w-full justify-between">
			<div class=" self-center text-xs font-medium">
				{$i18n.t('Tokens To Keep On Context Refresh (num_keep)')}
			</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition flex-shrink-0 outline-none"
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

		{#if (params?.num_keep ?? null) !== null}
			<div class="flex mt-0.5 space-x-2">
				<div class=" flex-1">
					<input
						id="steps-range"
						type="range"
						min="-1"
						max="10240000"
						step="1"
						bind:value={params.num_keep}
						class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
					/>
				</div>
				<div class="">
					<input
						bind:value={params.num_keep}
						type="number"
						class=" bg-transparent text-center w-14"
						min="-1"
						step="1"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<div class="flex w-full justify-between">
			<div class=" self-center text-xs font-medium">{$i18n.t('Max Tokens (num_predict)')}</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition flex-shrink-0 outline-none"
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

		{#if (params?.max_tokens ?? null) !== null}
			<div class="flex mt-0.5 space-x-2">
				<div class=" flex-1">
					<input
						id="steps-range"
						type="range"
						min="-2"
						max="131072"
						step="1"
						bind:value={params.max_tokens}
						class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
					/>
				</div>
				<div class="">
					<input
						bind:value={params.max_tokens}
						type="number"
						class=" bg-transparent text-center w-14"
						min="-2"
						step="1"
					/>
				</div>
			</div>
		{/if}
	</div>

	{#if admin}
		<div class=" py-0.5 w-full justify-between">
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs font-medium">{$i18n.t('use_mmap (Ollama)')}</div>

				<button
					class="p-1 px-3 text-xs flex rounded transition flex-shrink-0 outline-none"
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
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs font-medium">{$i18n.t('use_mlock (Ollama)')}</div>

				<button
					class="p-1 px-3 text-xs flex rounded transition flex-shrink-0 outline-none"
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
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs font-medium">{$i18n.t('num_thread (Ollama)')}</div>

				<button
					class="p-1 px-3 text-xs flex rounded transition flex-shrink-0 outline-none"
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

			{#if (params?.num_thread ?? null) !== null}
				<div class="flex mt-0.5 space-x-2">
					<div class=" flex-1">
						<input
							id="steps-range"
							type="range"
							min="1"
							max="256"
							step="1"
							bind:value={params.num_thread}
							class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
						/>
					</div>
					<div class="">
						<input
							bind:value={params.num_thread}
							type="number"
							class=" bg-transparent text-center w-14"
							min="1"
							max="256"
							step="1"
						/>
					</div>
				</div>
			{/if}
		</div>

		<div class=" py-0.5 w-full justify-between">
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs font-medium">{$i18n.t('num_gpu (Ollama)')}</div>

				<button
					class="p-1 px-3 text-xs flex rounded transition flex-shrink-0 outline-none"
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

			{#if (params?.num_gpu ?? null) !== null}
				<div class="flex mt-0.5 space-x-2">
					<div class=" flex-1">
						<input
							id="steps-range"
							type="range"
							min="0"
							max="256"
							step="1"
							bind:value={params.num_gpu}
							class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
						/>
					</div>
					<div class="">
						<input
							bind:value={params.num_gpu}
							type="number"
							class=" bg-transparent text-center w-14"
							min="0"
							max="256"
							step="1"
						/>
					</div>
				</div>
			{/if}
		</div>

		<!-- <div class=" py-0.5 w-full justify-between">
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs font-medium">{$i18n.t('Template')}</div>

				<button
					class="p-1 px-3 text-xs flex rounded transition flex-shrink-0 outline-none"
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
							class="px-3 py-1.5 text-sm w-full bg-transparent border dark:border-gray-600 outline-none rounded-lg -mb-1"
							placeholder="Write your model template content here"
							rows="4"
							bind:value={params.template}
						/>
					</div>
				</div>
			{/if}
		</div> -->
	{/if}
</div>
