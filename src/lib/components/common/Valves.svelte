<script>
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import Switch from './Switch.svelte';
	import MapSelector from './Valves/MapSelector.svelte';
	import { split } from 'postcss/lib/list';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	export let valvesSpec = null;
	export let valves = {};

	// Dynamic enum support
	let dynamicEnumCache = {};
	let dynamicEnumLoading = {};
	let dynamicEnums = {};

	/**
	 * Fetch dynamic enum options from an API endpoint
	 */
	async function fetchDynamicEnum(property, config) {
		// Normalize config to object format
		const normalizedConfig = typeof config === 'string' ? { endpoint: config } : config;

		const {
			endpoint,
			method = 'GET',
			response_path = null,
			value_field = 'id',
			label_field = null,
			cache_ttl = 300,
			fallback = []
		} = normalizedConfig;

		const cacheKey = endpoint;
		const now = Date.now();
		const fullUrl = `${WEBUI_API_BASE_URL}${endpoint}`;

		// Check cache
		if (
			dynamicEnumCache[cacheKey] &&
			now - dynamicEnumCache[cacheKey].timestamp < cache_ttl * 1000
		) {
			return dynamicEnumCache[cacheKey].data;
		}

		// Prevent duplicate simultaneous requests
		if (dynamicEnumLoading[cacheKey]) {
			return dynamicEnumLoading[cacheKey];
		}

		// Start fetch
		dynamicEnumLoading[cacheKey] = fetch(fullUrl, {
			method,
			headers: {
				Authorization: `Bearer ${localStorage.token}`,
				'Content-Type': 'application/json'
			}
		})
			.then(async (res) => {
				if (!res.ok) {
					throw new Error(`HTTP ${res.status}: ${res.statusText}`);
				}
				return res.json();
			})
			.then((data) => {
				// Extract array from response using response_path
				let items = data;
				if (response_path) {
					// Support dot notation for nested paths
					const pathParts = response_path.split('.');
					for (const part of pathParts) {
						items = items?.[part];
					}
				}

				// Ensure we have an array
				if (!Array.isArray(items)) {
					items = [items];
				}

				// Map to {value, label} format
				const options = items.map((item) => ({
					value: item[value_field],
					label: item[label_field || value_field]
				}));

				// Cache results
				dynamicEnumCache[cacheKey] = {
					data: options,
					timestamp: now
				};

				delete dynamicEnumLoading[cacheKey];
				return options;
			})
			.catch((err) => {
				console.error(`Failed to fetch dynamic enum from ${endpoint}:`, err);
				delete dynamicEnumLoading[cacheKey];

				// Return fallback options
				return fallback.length > 0 ? fallback : [];
			});

		return dynamicEnumLoading[cacheKey];
	}

	/**
	 * Refresh dynamic enum options for a specific property (clears cache)
	 */
	async function refreshDynamicEnum(property) {
		const spec = valvesSpec?.properties?.[property];
		const dynamicEnumConfig = spec?.dynamic_enum;

		if (!dynamicEnumConfig) return;

		// Clear cache for this endpoint
		const normalizedConfig =
			typeof dynamicEnumConfig === 'string' ? { endpoint: dynamicEnumConfig } : dynamicEnumConfig;
		const endpoint = normalizedConfig.endpoint;

		if (endpoint) {
			delete dynamicEnumCache[endpoint];
			delete dynamicEnumLoading[endpoint];
		}

		// Fetch fresh data
		try {
			const options = await fetchDynamicEnum(property, dynamicEnumConfig);
			dynamicEnums = { ...dynamicEnums, [property]: options };
		} catch (err) {
			console.error(`Error refreshing dynamic enum for ${property}:`, err);
		}
	}

	/**
	 * Initialize dynamic enums when the component mounts or valvesSpec changes
	 */
	async function initializeDynamicEnums() {
		if (!valvesSpec || !valvesSpec.properties) {
			return;
		}

		const newDynamicEnums = {};

		for (const property in valvesSpec.properties) {
			const spec = valvesSpec.properties[property];
			const dynamicEnumConfig = spec.dynamic_enum;

			if (dynamicEnumConfig) {
				try {
					const options = await fetchDynamicEnum(property, dynamicEnumConfig);
					newDynamicEnums[property] = options;
				} catch (err) {
					console.error(`Error initializing dynamic enum for ${property}:`, err);
					newDynamicEnums[property] = [];
				}
			}
		}

		// Reassign the entire object to trigger reactivity
		dynamicEnums = newDynamicEnums;
	}

	// Re-initialize when valvesSpec changes
	$: if (valvesSpec) {
		initializeDynamicEnums();
	}
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
							<!-- Static enum -->
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
						{:else if valvesSpec.properties[property]?.dynamic_enum}
							<!-- Dynamic enum -->
							<div class="flex items-center space-x-2">
								<select
									class="flex-1 rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100 dark:border-gray-850"
									bind:value={valves[property]}
									on:change={() => {
										dispatch('change');
									}}
								>
									{#if !dynamicEnums[property] || dynamicEnums[property].length === 0}
										<option value="" disabled>
											{dynamicEnumLoading[
												valvesSpec.properties[property].dynamic_enum?.endpoint ||
													valvesSpec.properties[property].dynamic_enum
											]
												? $i18n.t('Loading options...')
												: $i18n.t('No options available')}
										</option>
									{:else}
										{#each dynamicEnums[property] as option}
											<option value={option.value} selected={option.value === valves[property]}>
												{option.label}
											</option>
										{/each}
									{/if}
								</select>

								<!-- Refresh button -->
								<button
									type="button"
									class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition"
									title={$i18n.t('Refresh options')}
									on:click={() => refreshDynamicEnum(property)}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 20 20"
										fill="currentColor"
										class="w-4 h-4"
									>
										<path
											fill-rule="evenodd"
											d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z"
											clip-rule="evenodd"
										/>
									</svg>
								</button>
							</div>
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
											class=" w-full rounded-lg py-1 text-left text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100 dark:border-gray-850"
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
	<div class="text-xs">{$i18n.t('No valves')}</div>
{/if}
