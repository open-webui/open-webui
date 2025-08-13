<script>
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import Switch from './Switch.svelte';
	import MapSelector from './Valves/MapSelector.svelte';
	import { split } from 'postcss/lib/list';

	export let valvesSpec = null;
	export let valves = {};
	export let pinnedProperties = [];

	let sortedProperties = [];
	let pinnedSet = new Set(pinnedProperties);

	$: pinnedSet = new Set(pinnedProperties);

	$: if (valvesSpec && Object.keys(valvesSpec?.properties ?? {}).length) {
		const props = Object.keys(valvesSpec.properties);
		const pinned = props.filter((prop) => pinnedSet.has(prop));
		const unpinned = props.filter((prop) => !pinnedSet.has(prop));
		sortedProperties = [...pinned, ...unpinned];
	}
</script>

{#if valvesSpec && Object.keys(valvesSpec?.properties ?? {}).length}
	{#each sortedProperties as property, idx}
		<div class=" py-0.5 w-full justify-between">
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs font-medium flex items-center space-x-2">
					<span>
						{valvesSpec.properties[property].title}

						{#if (valvesSpec?.required ?? []).includes(property)}
							<span class=" text-gray-500">*required</span>
						{/if}
					</span>

					<!-- Pin/Unpin button -->
					<button
						class="text-xs opacity-50 hover:opacity-100 transition-opacity"
						type="button"
						title={pinnedSet.has(property) ? 'Unpin valve' : 'Pin valve'}
						on:click={() => {
							if (pinnedSet.has(property)) {
								pinnedProperties = pinnedProperties.filter((p) => p !== property);
							} else {
								pinnedProperties = [...pinnedProperties, property];
							}
							dispatch('pin', { property, pinned: pinnedSet.has(property) });
						}}
					>
						{#if pinnedSet.has(property)}
							📌
						{:else}
							📍
						{/if}
					</button>
				</div>

				<button
					class="p-1 px-3 text-xs flex rounded-sm transition"
					type="button"
					on:click={() => {
						valves[property] =
							(valves[property] ?? null) === null
								? (valvesSpec.properties[property]?.default ?? '')
								: null;

						dispatch('change');
					}}
				>
					{#if (valves[property] ?? null) === null}
						<span class="ml-2 self-center">
							{#if (valvesSpec?.required ?? []).includes(property)}
								{$i18n.t('None')}
							{:else}
								{$i18n.t('Default')}
							{/if}
						</span>
					{:else}
						<span class="ml-2 self-center"> {$i18n.t('Custom')} </span>
					{/if}
				</button>
			</div>

			{#if (valves[property] ?? null) !== null || valvesSpec.properties[property]?.input?.type === 'static' || valvesSpec.properties[property]?.input?.type === 'textbox' || valvesSpec.properties[property]?.input?.type === 'multiline'}
				<!-- {valves[property]} -->
				<div class="flex mt-0.5 mb-0.5 space-x-2">
					<div class=" flex-1">
						{#if valvesSpec.properties[property]?.enum ?? null}
							{#if valvesSpec.properties[property]?.input?.type === 'listview'}
								<!-- Multi-select listview -->
								<select
									class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100 dark:border-gray-850"
									bind:value={valves[property]}
									multiple
									size={Math.min(valvesSpec.properties[property].enum.length, 5)}
									on:change={() => {
										dispatch('change');
									}}
								>
									{#each valvesSpec.properties[property].enum as option}
										<option value={option}>
											{option}
										</option>
									{/each}
								</select>
							{:else}
								<!-- Single-select dropdown (default and combobox) -->
								<select
									class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100 dark:border-gray-850"
									bind:value={valves[property]}
									on:change={() => {
										dispatch('change');
									}}
								>
									{#each valvesSpec.properties[property].enum as option}
										<option value={option} selected={option === valves[property]}>
											{option}
										</option>
									{/each}
								</select>
							{/if}
						{:else if (valvesSpec.properties[property]?.type ?? null) === 'boolean'}
							<div class="flex justify-between items-center">
								<div class="text-xs text-gray-500">
									{valves[property] ? 'Enabled' : 'Disabled'}
								</div>

								<div class=" pr-2">
									<Switch
										bind:state={valves[property]}
										on:change={() => {
											dispatch('change');
										}}
									/>
								</div>
							</div>
						{:else if (valvesSpec.properties[property]?.type ?? null) === 'number' || (valvesSpec.properties[property]?.type ?? null) === 'integer'}
							{#if valvesSpec.properties[property]?.input?.type === 'slider'}
								<div class="flex flex-col space-y-2">
									<div class="flex justify-between text-xs text-gray-500">
										<span>Min: {valvesSpec.properties[property]?.minimum ?? 0}</span>
										<span class="font-medium text-gray-700 dark:text-gray-300"
											>Value: {valves[property]}</span
										>
										<span>Max: {valvesSpec.properties[property]?.maximum ?? 100}</span>
									</div>
									<input
										type="range"
										min={valvesSpec.properties[property]?.minimum ?? 0}
										max={valvesSpec.properties[property]?.maximum ?? 100}
										step={valvesSpec.properties[property]?.step ?? 1}
										class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700 slider"
										bind:value={valves[property]}
										on:input={() => {
											dispatch('change');
										}}
									/>
								</div>
							{:else}
								<input
									class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100 dark:border-gray-850"
									type="number"
									placeholder={valvesSpec.properties[property].title}
									bind:value={valves[property]}
									min={valvesSpec.properties[property]?.minimum}
									max={valvesSpec.properties[property]?.maximum}
									step={valvesSpec.properties[property]?.step}
									autocomplete="off"
									required
									on:change={() => {
										dispatch('change');
									}}
								/>
							{/if}
						{:else if (valvesSpec.properties[property]?.type ?? null) !== 'string'}
							<input
								class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100 dark:border-gray-850"
								type="text"
								placeholder={valvesSpec.properties[property].title}
								bind:value={valves[property]}
								autocomplete="off"
								required
								on:change={() => {
									dispatch('change');
								}}
							/>
						{:else if valvesSpec.properties[property]?.input ?? null}
							{#if valvesSpec.properties[property]?.input?.type === 'color'}
								<div class="flex items-center space-x-2">
									<div class="relative size-6">
										<input
											type="color"
											class="size-6 rounded cursor-pointer border border-gray-200 dark:border-gray-700"
											value={valves[property] ?? '#000000'}
											on:input={(e) => {
												// Convert the color value to uppercase immediately
												valves[property] = e.target.value.toUpperCase();
												dispatch('change');
											}}
										/>
									</div>

									<input
										type="text"
										class="flex-1 rounded-lg py-2 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100 dark:border-gray-850"
										placeholder="Enter hex color (e.g. #FF0000)"
										bind:value={valves[property]}
										autocomplete="off"
										disabled
										on:change={() => {
											dispatch('change');
										}}
									/>
								</div>
							{:else if valvesSpec.properties[property]?.input?.type === 'map'}
								<!-- EXPERIMENTAL INPUT TYPE, DO NOT USE IN PRODUCTION -->
								<div class="flex flex-col items-center gap-1">
									<MapSelector
										setViewLocation={((valves[property] ?? '').includes(',') ?? false)
											? valves[property].split(',')
											: null}
										onClick={(value) => {
											valves[property] = value;
											dispatch('change');
										}}
									/>

									{#if valves[property]}
										<input
											type="text"
											class=" w-full rounded-lg py-1 text-left text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100 dark:border-gray-850"
											placeholder="Enter coordinates (e.g. 51.505, -0.09)"
											bind:value={valves[property]}
											autocomplete="off"
											on:change={() => {
												dispatch('change');
											}}
										/>
									{/if}
								</div>
							{:else if valvesSpec.properties[property]?.input?.type === 'static' || valvesSpec.properties[property]?.input?.type === 'static_text'}
								<!-- Static text - display only, no input -->
								<div
									class="bg-gray-50 dark:bg-gray-800 rounded-lg py-2 px-4 text-sm text-gray-700 dark:text-gray-300"
								>
									{valvesSpec.properties[property]?.input?.value ||
										valvesSpec.properties[property]?.default ||
										valvesSpec.properties[property].title}
								</div>
							{:else if valvesSpec.properties[property]?.input?.type === 'static_multiline'}
								<!-- Static multiline text - display only, no input -->
								<div
									class="bg-gray-50 dark:bg-gray-800 rounded-lg py-3 px-4 text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap min-h-20"
								>
									{valvesSpec.properties[property]?.input?.value ||
										valvesSpec.properties[property]?.default ||
										valvesSpec.properties[property].title}
								</div>
							{:else if valvesSpec.properties[property]?.input?.type === 'textbox' || valvesSpec.properties[property]?.input?.type === 'multiline'}
								<!-- Textbox/multiline textarea in INPUT CONFIG section -->
								<textarea
									class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100 dark:border-gray-850 min-h-20"
									placeholder={valvesSpec.properties[property].title}
									bind:value={valves[property]}
									rows={valvesSpec.properties[property]?.input?.rows ?? 4}
									autocomplete="off"
									required
									on:change={() => {
										dispatch('change');
									}}
								/>
							{/if}
						{:else if valvesSpec.properties[property]?.input?.type === 'textbox' || valvesSpec.properties[property]?.input?.type === 'multiline'}
							<textarea
								class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100 dark:border-gray-850 min-h-20"
								placeholder={valvesSpec.properties[property].title}
								bind:value={valves[property]}
								rows={valvesSpec.properties[property]?.input?.rows ?? 4}
								autocomplete="off"
								required
								on:change={() => {
									dispatch('change');
								}}
							/>
						{:else}
							<textarea
								class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100 dark:border-gray-850"
								placeholder={valvesSpec.properties[property].title}
								bind:value={valves[property]}
								autocomplete="off"
								required
								on:change={() => {
									dispatch('change');
								}}
							/>
						{/if}
					</div>
				</div>
			{/if}

			{#if (valvesSpec.properties[property]?.description ?? null) !== null}
				<div class="text-xs text-gray-500">
					{valvesSpec.properties[property].description}
				</div>
			{/if}
		</div>
	{/each}
{:else}
	<div class="text-xs">No valves</div>
{/if}

<style>
	/* Slider styling */
	.slider::-webkit-slider-thumb {
		appearance: none;
		height: 16px;
		width: 16px;
		border-radius: 50%;
		background: #3b82f6;
		cursor: pointer;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
	}

	.slider::-moz-range-thumb {
		height: 16px;
		width: 16px;
		border-radius: 50%;
		background: #3b82f6;
		cursor: pointer;
		border: none;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
	}

	.slider::-webkit-slider-track {
		background: transparent;
	}
</style>
