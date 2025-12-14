<script>
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import Switch from './Switch.svelte';
	import MapSelector from './Valves/MapSelector.svelte';

	export let valvesSpec = null;
	export let valves = {};
</script>

{#if valvesSpec && Object.keys(valvesSpec?.properties ?? {}).length}
	{#each Object.keys(valvesSpec.properties) as property, idx}
		<div class=" py-0.5 w-full justify-between">
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs font-medium">
					{valvesSpec.properties[property].title}

					{#if (valvesSpec?.required ?? []).includes(property)}
						<span class=" text-gray-500">*required</span>
					{/if}
				</div>

				<button
					class="p-1 px-3 text-xs flex rounded-sm transition"
					type="button"
					on:click={() => {
						const propertySpec = valvesSpec.properties[property] ?? {};

						if ((valves[property] ?? null) === null) {
							// Initialize to custom value
							if ((propertySpec?.type ?? null) === 'array') {
								const defaultArray = propertySpec?.default ?? [];
								valves[property] = Array.isArray(defaultArray) ? defaultArray.join(', ') : '';
							} else {
								valves[property] = propertySpec?.default ?? '';
							}
						} else {
							valves[property] = null;
						}

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

			{#if (valves[property] ?? null) !== null}
				<!-- {valves[property]} -->
				<div class="flex mt-0.5 mb-0.5 space-x-2">
					<div class=" flex-1">
						{#if valvesSpec.properties[property]?.enum ?? null}
							<select
								class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100/30 dark:border-gray-850/30"
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
						{:else if (valvesSpec.properties[property]?.type ?? null) === 'boolean'}
							<div class="flex justify-between items-center">
								<div class="text-xs text-gray-500">
									{valves[property] ? $i18n.t('Enabled') : $i18n.t('Disabled')}
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
						{:else if (valvesSpec.properties[property]?.type ?? null) !== 'string'}
							<input
								class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100/30 dark:border-gray-850/30"
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
										class="flex-1 rounded-lg py-2 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100/30 dark:border-gray-850/30"
										placeholder={$i18n.t('Enter hex color (e.g. #FF0000)')}
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
											class=" w-full rounded-lg py-1 text-left text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100/30 dark:border-gray-850/30"
											placeholder={$i18n.t('Enter coordinates (e.g. 51.505, -0.09)')}
											bind:value={valves[property]}
											autocomplete="off"
											on:change={() => {
												dispatch('change');
											}}
										/>
									{/if}
								</div>
							{/if}
						{:else}
							<textarea
								class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100/30 dark:border-gray-850/30"
								placeholder={valvesSpec.properties[property].title}
								bind:value={valves[property]}
								autocomplete="off"
								required
								on:change={() => {
									dispatch('change');
								}}
							></textarea>
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
	<div class="text-xs">{$i18n.t('No valves')}</div>
{/if}
