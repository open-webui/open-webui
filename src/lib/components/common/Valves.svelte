<script>
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import Switch from './Switch.svelte';

	export let valvesSpec = null;
	export let valves = {};

	function isHexColor(value) {
		return typeof value === 'string' && /^#([0-9A-F]{3}){1,2}$/i.test(value);
	}

	function validateHexColor(value) {
		let cleaned = value.replace(/[^0-9A-Fa-f]/gi, '');
		cleaned = cleaned.slice(0, 6);
		// If we have 3 or 6 valid hex chars, it's a valid color
		if (cleaned.length === 3 || cleaned.length === 6) {
			return '#' + cleaned.toUpperCase();
		}
		// For incomplete values, still prefix with # but don't validate fully
		if (cleaned.length > 0) {
			return '#' + cleaned.toUpperCase();
		}
		return '#000000';
	}

	// Function to expand shorthand hex colors (#RGB to #RRGGBB)
	function expandHexColor(hex) {
		if (hex && hex.length === 4 && hex.startsWith('#')) {
			return '#' +
				hex[1] + hex[1] +
				hex[2] + hex[2] +
				hex[3] + hex[3];
		}
		return hex;
	}

	// Function to ensure proper format for color picker
	function getColorPickerValue(hexColor) {
		// Color picker needs 6-digit hex
		if (isHexColor(hexColor)) {
			const expanded = expandHexColor(hexColor);
			return expanded.toLowerCase(); // HTML color inputs expect lowercase
		}
		return '#000000';
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

			{#if (valves[property] ?? null) !== null}
				<!-- {valves[property]} -->
				<div class="flex mt-0.5 mb-1.5 space-x-2">
					<div class=" flex-1">
						{#if valvesSpec.properties[property]?.enum ?? null}
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
						{:else if isHexColor(valvesSpec.properties[property]?.default)}
							<div class="flex items-center space-x-2">
								<div class="relative w-8 h-8">
									<input
										type="color"
										class="w-8 h-8 rounded cursor-pointer border border-gray-200 dark:border-gray-700 {!isHexColor(valves[property]) ? 'opacity-70' : ''}"
										value={getColorPickerValue(isHexColor(valves[property]) ? valves[property] : '#000000')}
										on:input={(e) => {
											// Convert the color value to uppercase immediately
											valves[property] = e.target.value.toUpperCase();
											dispatch('change');
										}}
									/>

									{#if !isHexColor(valves[property])}
										<div class="absolute top-0 right-0 w-3 h-3 bg-yellow-500 rounded-full flex items-center justify-center"
											 title="Current value is not a valid hex color">
											<span class="text-white text-[8px]">!</span>
										</div>
									{/if}
								</div>

								<input
									type="text"
									class="flex-1 rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100 dark:border-gray-850 {!isHexColor(valves[property]) ? 'border-yellow-500' : ''}"
									placeholder="Enter hex color (e.g. #FF0000)"
									value={valves[property]}
									on:input={(e) => {
										// Only update if value changed to avoid cursor jumping
										const newValue = e.target.value.startsWith('#')
											? e.target.value
											: '#' + e.target.value.replace('#', '');
										valves[property] = newValue;
									}}
									on:blur={() => {
										valves[property] = validateHexColor(valves[property]);
										dispatch('change');
									}}
								/>
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
