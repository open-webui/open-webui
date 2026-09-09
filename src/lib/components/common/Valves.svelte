<script>
	import { getContext, createEventDispatcher } from 'svelte';
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';
	import { localizeValvesSchema, resolveLocalizedString } from '$lib/utils/localizedContent';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import Switch from './Switch.svelte';
	import SensitiveInput from './SensitiveInput.svelte';
	import NativeSelect from './NativeSelect.svelte';
	import MultiSelect from './MultiSelect.svelte';
	import MapSelector from './Valves/MapSelector.svelte';

	export let valvesSpec = null;
	export let valves = {};
	export let meta = {};
	export let userValves = false;
	$: prefix = userValves ? 'user_valves' : 'valves';
	$: displaySpec = localizeValvesSchema(valvesSpec, $i18n.language, meta, prefix);
</script>

{#if displaySpec && Object.keys(displaySpec?.properties ?? {}).length}
	{#each Object.keys(displaySpec.properties) as property}
		<div class=" py-0.5 w-full justify-between">
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs font-normal">
					{displaySpec.properties[property].title}

					{#if (displaySpec?.required ?? []).includes(property)}
						<span class=" text-gray-500">{$i18n.t('*required')}</span>
					{/if}
				</div>

				<button
					class="px-2 py-1 text-xs flex rounded-lg transition hover:bg-gray-50/70 dark:hover:bg-gray-850/50"
					type="button"
					on:click={() => {
						const propertySpec = displaySpec.properties[property] ?? {};

						if ((valves[property] ?? null) === null) {
							// Initialize to custom value
							if ((propertySpec?.type ?? null) === 'array') {
								const defaultArray = propertySpec?.default ?? [];
								if (propertySpec?.input?.type === 'multiselect') {
									valves[property] = Array.isArray(defaultArray) ? [...defaultArray] : [];
								} else {
									valves[property] = Array.isArray(defaultArray) ? defaultArray.join(', ') : '';
								}
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
							{#if (displaySpec?.required ?? []).includes(property)}
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
					<div class=" flex-1 min-w-0">
						{#if displaySpec.properties[property]?.enum ?? null}
							<select
								class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100/30 dark:border-gray-850/30"
								bind:value={valves[property]}
								on:change={() => {
									dispatch('change');
								}}
							>
								{#each displaySpec.properties[property].enum as option}
									<option value={option} selected={option === valves[property]}>
										{resolveLocalizedString(
											String(option),
											meta?.i18n,
											$i18n.language,
											`${prefix}.${property}.enum.${option}`
										)}
									</option>
								{/each}
							</select>
						{:else if (displaySpec.properties[property]?.type ?? null) === 'boolean'}
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
						{:else if displaySpec.properties[property]?.input?.type === 'multiselect' && displaySpec.properties[property]?.input?.options}
							<MultiSelect
								className="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100/30 dark:border-gray-850/30"
								bind:value={valves[property]}
								options={displaySpec.properties[property].input.options}
								placeholder={$i18n.t('Select options')}
								on:change={() => {
									dispatch('change');
								}}
							/>
						{:else if (displaySpec.properties[property]?.type ?? null) !== 'string'}
							<input
								class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100/30 dark:border-gray-850/30"
								type="text"
								placeholder={displaySpec.properties[property].title}
								bind:value={valves[property]}
								autocomplete="off"
								required
								on:change={() => {
									dispatch('change');
								}}
							/>
						{:else if displaySpec.properties[property]?.input ?? null}
							{#if displaySpec.properties[property]?.input?.type === 'password'}
								<div
									class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 border border-gray-100/30 dark:border-gray-850/30"
								>
									<SensitiveInput
										id="valve-{property}"
										placeholder={displaySpec.properties[property]?.description ?? ''}
										bind:value={valves[property]}
										required={(displaySpec?.required ?? []).includes(property)}
										on:change={() => {
											dispatch('change');
										}}
									/>
								</div>
							{:else if displaySpec.properties[property]?.input?.type === 'select' && displaySpec.properties[property]?.input?.options}
								<NativeSelect
									className="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100/30 dark:border-gray-850/30"
									bind:value={valves[property]}
									options={displaySpec.properties[property].input.options}
									placeholder={displaySpec.properties[property]?.description ??
										$i18n.t('Select an option')}
									on:change={() => {
										dispatch('change');
									}}
								/>
							{:else if displaySpec.properties[property]?.input?.type === 'color'}
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
							{:else if displaySpec.properties[property]?.input?.type === 'map'}
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
								placeholder={displaySpec.properties[property].title}
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

			{#if (displaySpec.properties[property]?.description ?? null) !== null}
				<div class="markdown-prose-xs max-w-full text-gray-500 dark:text-gray-400">
					<!-- eslint-disable-next-line svelte/no-at-html-tags -->
					{@html DOMPurify.sanitize(
						marked.parse(displaySpec.properties[property].description ?? '', { async: false })
					)}
				</div>
			{/if}
		</div>
	{/each}
{:else}
	<div class="text-xs">{$i18n.t('No valves')}</div>
{/if}
