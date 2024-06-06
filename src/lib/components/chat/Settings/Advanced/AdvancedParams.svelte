<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	export let params = {
		// Advanced
		seed: 0,
		stop: null,
		temperature: '',
		frequency_penalty: '',
		repeat_last_n: '',
		mirostat: '',
		mirostat_eta: '',
		mirostat_tau: '',
		top_k: '',
		top_p: '',
		tfs_z: '',
		num_ctx: '',
		max_tokens: '',
		use_mmap: null,
		use_mlock: null,
		num_thread: null,
		template: null
	};

	let customFieldName = '';
	let customFieldValue = '';

	$: if (params) {
		dispatch('change', params);
	}
</script>

<div class=" space-y-1 text-xs">
	<div class=" py-0.5 w-full justify-between">
		<div class="flex w-full justify-between">
			<div class=" self-center text-xs font-medium">{$i18n.t('Seed')}</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition"
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
				class="p-1 px-3 text-xs flex rounded transition"
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
				class="p-1 px-3 text-xs flex rounded transition"
				type="button"
				on:click={() => {
					params.temperature = (params?.temperature ?? '') === '' ? 0.8 : '';
				}}
			>
				{#if (params?.temperature ?? '') === ''}
					<span class="ml-2 self-center"> {$i18n.t('Default')} </span>
				{:else}
					<span class="ml-2 self-center"> {$i18n.t('Custom')} </span>
				{/if}
			</button>
		</div>

		{#if (params?.temperature ?? '') !== ''}
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
						step="0.05"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<div class="flex w-full justify-between">
			<div class=" self-center text-xs font-medium">{$i18n.t('Mirostat')}</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition"
				type="button"
				on:click={() => {
					params.mirostat = (params?.mirostat ?? '') === '' ? 0 : '';
				}}
			>
				{#if (params?.mirostat ?? '') === ''}
					<span class="ml-2 self-center">{$i18n.t('Default')}</span>
				{:else}
					<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
				{/if}
			</button>
		</div>

		{#if (params?.mirostat ?? '') !== ''}
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
				class="p-1 px-3 text-xs flex rounded transition"
				type="button"
				on:click={() => {
					params.mirostat_eta = (params?.mirostat_eta ?? '') === '' ? 0.1 : '';
				}}
			>
				{#if (params?.mirostat_eta ?? '') === ''}
					<span class="ml-2 self-center">{$i18n.t('Default')}</span>
				{:else}
					<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
				{/if}
			</button>
		</div>

		{#if (params?.mirostat_eta ?? '') !== ''}
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
						step="0.05"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<div class="flex w-full justify-between">
			<div class=" self-center text-xs font-medium">{$i18n.t('Mirostat Tau')}</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition"
				type="button"
				on:click={() => {
					params.mirostat_tau = (params?.mirostat_tau ?? '') === '' ? 5.0 : '';
				}}
			>
				{#if (params?.mirostat_tau ?? '') === ''}
					<span class="ml-2 self-center">{$i18n.t('Default')}</span>
				{:else}
					<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
				{/if}
			</button>
		</div>

		{#if (params?.mirostat_tau ?? '') !== ''}
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
						step="0.5"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<div class="flex w-full justify-between">
			<div class=" self-center text-xs font-medium">{$i18n.t('Top K')}</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition"
				type="button"
				on:click={() => {
					params.top_k = (params?.top_k ?? '') === '' ? 40 : '';
				}}
			>
				{#if (params?.top_k ?? '') === ''}
					<span class="ml-2 self-center">{$i18n.t('Default')}</span>
				{:else}
					<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
				{/if}
			</button>
		</div>

		{#if (params?.top_k ?? '') !== ''}
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
						step="0.5"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<div class="flex w-full justify-between">
			<div class=" self-center text-xs font-medium">{$i18n.t('Top P')}</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition"
				type="button"
				on:click={() => {
					params.top_p = (params?.top_p ?? '') === '' ? 0.9 : '';
				}}
			>
				{#if (params?.top_p ?? '') === ''}
					<span class="ml-2 self-center">{$i18n.t('Default')}</span>
				{:else}
					<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
				{/if}
			</button>
		</div>

		{#if (params?.top_p ?? '') !== ''}
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
						step="0.05"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<div class="flex w-full justify-between">
			<div class=" self-center text-xs font-medium">{$i18n.t('Frequency Penalty')}</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition"
				type="button"
				on:click={() => {
					params.frequency_penalty = (params?.frequency_penalty ?? '') === '' ? 1.1 : '';
				}}
			>
				{#if (params?.frequency_penalty ?? '') === ''}
					<span class="ml-2 self-center">{$i18n.t('Default')}</span>
				{:else}
					<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
				{/if}
			</button>
		</div>

		{#if (params?.frequency_penalty ?? '') !== ''}
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
						step="0.05"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<div class="flex w-full justify-between">
			<div class=" self-center text-xs font-medium">{$i18n.t('Repeat Last N')}</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition"
				type="button"
				on:click={() => {
					params.repeat_last_n = (params?.repeat_last_n ?? '') === '' ? 64 : '';
				}}
			>
				{#if (params?.repeat_last_n ?? '') === ''}
					<span class="ml-2 self-center">{$i18n.t('Default')}</span>
				{:else}
					<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
				{/if}
			</button>
		</div>

		{#if (params?.repeat_last_n ?? '') !== ''}
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
				class="p-1 px-3 text-xs flex rounded transition"
				type="button"
				on:click={() => {
					params.tfs_z = (params?.tfs_z ?? '') === '' ? 1 : '';
				}}
			>
				{#if (params?.tfs_z ?? '') === ''}
					<span class="ml-2 self-center">{$i18n.t('Default')}</span>
				{:else}
					<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
				{/if}
			</button>
		</div>

		{#if (params?.tfs_z ?? '') !== ''}
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
						step="0.05"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<div class="flex w-full justify-between">
			<div class=" self-center text-xs font-medium">{$i18n.t('Context Length')}</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition"
				type="button"
				on:click={() => {
					params.num_ctx = (params?.num_ctx ?? '') === '' ? 2048 : '';
				}}
			>
				{#if (params?.num_ctx ?? '') === ''}
					<span class="ml-2 self-center">{$i18n.t('Default')}</span>
				{:else}
					<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
				{/if}
			</button>
		</div>

		{#if (params?.num_ctx ?? '') !== ''}
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
						step="10"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<div class="flex w-full justify-between">
			<div class=" self-center text-xs font-medium">{$i18n.t('Max Tokens (num_predict)')}</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition"
				type="button"
				on:click={() => {
					params.max_tokens = (params?.max_tokens ?? '') === '' ? 128 : '';
				}}
			>
				{#if (params?.max_tokens ?? '') === ''}
					<span class="ml-2 self-center">{$i18n.t('Default')}</span>
				{:else}
					<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
				{/if}
			</button>
		</div>

		{#if (params?.max_tokens ?? '') !== ''}
			<div class="flex mt-0.5 space-x-2">
				<div class=" flex-1">
					<input
						id="steps-range"
						type="range"
						min="-2"
						max="16000"
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
						max="16000"
						step="1"
					/>
				</div>
			</div>
		{/if}
	</div>

	<div class=" py-0.5 w-full justify-between">
		<div class="flex w-full justify-between">
			<div class=" self-center text-xs font-medium">{$i18n.t('use_mmap (Ollama)')}</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition"
				type="button"
				on:click={() => {
					params.use_mmap = (params?.use_mmap ?? null) === null ? true : null;
				}}
			>
				{#if (params?.use_mmap ?? null) === null}
					<span class="ml-2 self-center">{$i18n.t('Default')}</span>
				{:else}
					<span class="ml-2 self-center">{$i18n.t('On')}</span>
				{/if}
			</button>
		</div>
	</div>

	<div class=" py-0.5 w-full justify-between">
		<div class="flex w-full justify-between">
			<div class=" self-center text-xs font-medium">{$i18n.t('use_mlock (Ollama)')}</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition"
				type="button"
				on:click={() => {
					params.use_mlock = (params?.use_mlock ?? null) === null ? true : null;
				}}
			>
				{#if (params?.use_mlock ?? null) === null}
					<span class="ml-2 self-center">{$i18n.t('Default')}</span>
				{:else}
					<span class="ml-2 self-center">{$i18n.t('On')}</span>
				{/if}
			</button>
		</div>
	</div>

	<div class=" py-0.5 w-full justify-between">
		<div class="flex w-full justify-between">
			<div class=" self-center text-xs font-medium">{$i18n.t('num_thread (Ollama)')}</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition"
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
			<div class=" self-center text-xs font-medium">{$i18n.t('Template')}</div>

			<button
				class="p-1 px-3 text-xs flex rounded transition"
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
	</div>
</div>
