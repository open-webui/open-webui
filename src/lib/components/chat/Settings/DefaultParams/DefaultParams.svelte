<script lang="ts">
	import { getContext } from 'svelte';


	const i18n = getContext('i18n');

	export let title =  $i18n.t('Default Parameters')

	// Default
	export let showParams: boolean = false;

	export let options = {
		seed: 0,
		temperature: '',
		repetition_penalty: '',
		top_k: '',
		top_p: '',
		num_predict: '',
	};

</script>

<div class="mt-2 space-y-3 pr-1.5">
	<div class="flex justify-between items-center text-sm">
		<div class="  font-medium">{title}</div>
		<button
			class=" text-xs font-medium text-gray-500"
			type="button"
			on:click={() => {
				showParams = !showParams;
			}}>{showParams ? $i18n.t('Hide') : $i18n.t('Show')}</button
		>
	</div>

	{#if showParams}
	<div class=" space-y-3 text-xs">
		<div>
			<div class=" py-0.5 flex w-full justify-between">
				<div class=" w-20 text-xs font-medium self-center">{$i18n.t('Seed')}</div>
				<div class=" flex-1 self-center">
					<input
						class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
						type="number"
						placeholder="Enter Seed"
						bind:value={options.seed}
						autocomplete="off"
						min="0"
					/>
				</div>
			</div>
		</div>
	
		<div class=" py-0.5 w-full justify-between">
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs font-medium">{$i18n.t('Temperature')}</div>
	
				<button
					class="p-1 px-3 text-xs flex rounded transition"
					type="button"
					on:click={() => {
						options.temperature = options.temperature === '' ? 0.8 : '';
					}}
				>
					{#if options.temperature === ''}
						<span class="ml-2 self-center"> {$i18n.t('Default')} </span>
					{:else}
						<span class="ml-2 self-center"> {$i18n.t('Custom')} </span>
					{/if}
				</button>
			</div>
	
			{#if options.temperature !== ''}
				<div class="flex mt-0.5 space-x-2">
					<div class=" flex-1">
						<input
							id="steps-range"
							type="range"
							min="0"
							max="1"
							step="0.05"
							bind:value={options.temperature}
							class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
						/>
					</div>
					<div>
						<input
							bind:value={options.temperature}
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
				<div class=" self-center text-xs font-medium">{$i18n.t('Top K')}</div>
	
				<button
					class="p-1 px-3 text-xs flex rounded transition"
					type="button"
					on:click={() => {
						options.top_k = options.top_k === '' ? 40 : '';
					}}
				>
					{#if options.top_k === ''}
						<span class="ml-2 self-center">{$i18n.t('Default')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
					{/if}
				</button>
			</div>
	
			{#if options.top_k !== ''}
				<div class="flex mt-0.5 space-x-2">
					<div class=" flex-1">
						<input
							id="steps-range"
							type="range"
							min="0"
							max="100"
							step="0.5"
							bind:value={options.top_k}
							class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
						/>
					</div>
					<div>
						<input
							bind:value={options.top_k}
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
						options.top_p = options.top_p === '' ? 0.9 : '';
					}}
				>
					{#if options.top_p === ''}
						<span class="ml-2 self-center">{$i18n.t('Default')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
					{/if}
				</button>
			</div>
	
			{#if options.top_p !== ''}
				<div class="flex mt-0.5 space-x-2">
					<div class=" flex-1">
						<input
							id="steps-range"
							type="range"
							min="0"
							max="1"
							step="0.05"
							bind:value={options.top_p}
							class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
						/>
					</div>
					<div>
						<input
							bind:value={options.top_p}
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
				<div class=" self-center text-xs font-medium">{$i18n.t('Repeat Penalty')}</div>
	
				<button
					class="p-1 px-3 text-xs flex rounded transition"
					type="button"
					on:click={() => {
						options.repetition_penalty = options.repetition_penalty === '' ? 1.1 : '';
					}}
				>
					{#if options.repetition_penalty === ''}
						<span class="ml-2 self-center">{$i18n.t('Default')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
					{/if}
				</button>
			</div>
	
			{#if options.repetition_penalty !== ''}
				<div class="flex mt-0.5 space-x-2">
					<div class=" flex-1">
						<input
							id="steps-range"
							type="range"
							min="0"
							max="2"
							step="0.05"
							bind:value={options.repetition_penalty}
							class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
						/>
					</div>
					<div>
						<input
							bind:value={options.repetition_penalty}
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
				<div class=" self-center text-xs font-medium">{$i18n.t('Max Tokens')}</div>
	
				<button
					class="p-1 px-3 text-xs flex rounded transition"
					type="button"
					on:click={() => {
						options.num_predict = options.num_predict === '' ? 128 : '';
					}}
				>
					{#if !options.num_predict}
						<span class="ml-2 self-center">{$i18n.t('Default')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
					{/if}
				</button>
			</div>
	
			{#if options.num_predict}
				<div class="flex mt-0.5 space-x-2">
					<div class=" flex-1">
						<input
							id="steps-range"
							type="range"
							min="-2"
							max="16000"
							step="1"
							bind:value={options.num_predict}
							class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
						/>
					</div>
					<div class="">
						<input
							bind:value={options.num_predict}
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
	</div>
	{/if}
</div>
