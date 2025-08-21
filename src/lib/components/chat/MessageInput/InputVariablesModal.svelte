<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';
	import { models, config } from '$lib/stores';

	import { toast } from 'svelte-sonner';
	import { copyToClipboard } from '$lib/utils';

	import XMark from '$lib/components/icons/XMark.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import MapSelector from '$lib/components/common/Valves/MapSelector.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let variables = {};

	export let onSave = (e) => {};

	let loading = false;
	let variableValues = {};

	const submitHandler = async () => {
		onSave(variableValues);
		show = false;
	};

	const init = async () => {
		loading = true;
		variableValues = {};
		for (const variable of Object.keys(variables)) {
			if (variables[variable]?.default !== undefined) {
				variableValues[variable] = variables[variable].default;
			} else {
				variableValues[variable] = '';
			}
		}
		loading = false;

		await tick();

		const firstInputElement = document.getElementById('input-variable-0');
		if (firstInputElement) {
			console.log('Focusing first input element:', firstInputElement);
			firstInputElement.focus();
		}
	};

	$: if (show) {
		init();
	}
</script>

<Modal bind:show size="md">
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-2">
			<div class=" text-lg font-medium self-center">{$i18n.t('Input Variables')}</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-5 pb-4 md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div class="px-1">
						{#if !loading}
							<div class="flex flex-col gap-1">
								{#each Object.keys(variables) as variable, idx}
									{@const { type, ...variableAttributes } = variables[variable] ?? {}}

									<div class=" py-0.5 w-full justify-between">
										<div class="flex w-full justify-between mb-1.5">
											<div class=" self-center text-xs font-medium">
												{variable}

												{#if variables[variable]?.required ?? true}
													<span class=" text-gray-500">*required</span>
												{/if}
											</div>
										</div>

										<div class="flex mt-0.5 mb-0.5 space-x-2">
											<div class=" flex-1">
												{#if variables[variable]?.type === 'select'}
													{@const options = variableAttributes?.options ?? []}
													{@const placeholder = variableAttributes?.placeholder ?? ''}

													<select
														class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100 dark:border-gray-850"
														bind:value={variableValues[variable]}
														id="input-variable-{idx}"
													>
														{#if placeholder}
															<option value="" disabled selected>
																{placeholder}
															</option>
														{/if}
														{#each options as option}
															<option value={option} selected={option === variableValues[variable]}>
																{option}
															</option>
														{/each}
													</select>
												{:else if variables[variable]?.type === 'checkbox'}
													<div class="flex items-center space-x-2">
														<div class="relative flex justify-center items-center gap-2">
															<input
																type="checkbox"
																bind:checked={variableValues[variable]}
																class="size-3.5 rounded cursor-pointer border border-gray-200 dark:border-gray-700"
																id="input-variable-{idx}"
																{...variableAttributes}
															/>

															<label for="input-variable-{idx}" class="text-sm"
																>{variables[variable]?.label ?? variable}</label
															>
														</div>

														<input
															type="text"
															class="flex-1 py-1 text-sm dark:text-gray-300 bg-transparent outline-hidden"
															placeholder={$i18n.t('Enter value (true/false)')}
															bind:value={variableValues[variable]}
															autocomplete="off"
															required
														/>
													</div>
												{:else if variables[variable]?.type === 'color'}
													<div class="flex items-center space-x-2">
														<div class="relative size-6">
															<input
																type="color"
																class="size-6 rounded cursor-pointer border border-gray-200 dark:border-gray-700"
																value={variableValues[variable]}
																id="input-variable-{idx}"
																on:input={(e) => {
																	// Convert the color value to uppercase immediately
																	variableValues[variable] = e.target.value.toUpperCase();
																}}
																{...variableAttributes}
															/>
														</div>

														<input
															type="text"
															class="flex-1 py-2 text-sm dark:text-gray-300 bg-transparent outline-hidden"
															placeholder={$i18n.t('Enter hex color (e.g. #FF0000)')}
															bind:value={variableValues[variable]}
															autocomplete="off"
															required
														/>
													</div>
												{:else if variables[variable]?.type === 'date'}
													<input
														type="date"
														class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100 dark:border-gray-850"
														placeholder={variables[variable]?.placeholder ?? ''}
														bind:value={variableValues[variable]}
														autocomplete="off"
														id="input-variable-{idx}"
														required
														{...variableAttributes}
													/>
												{:else if variables[variable]?.type === 'datetime-local'}
													<input
														type="datetime-local"
														class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100 dark:border-gray-850"
														placeholder={variables[variable]?.placeholder ?? ''}
														bind:value={variableValues[variable]}
														autocomplete="off"
														id="input-variable-{idx}"
														required
														{...variableAttributes}
													/>
												{:else if variables[variable]?.type === 'email'}
													<input
														type="email"
														class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100 dark:border-gray-850"
														placeholder={variables[variable]?.placeholder ?? ''}
														bind:value={variableValues[variable]}
														autocomplete="off"
														id="input-variable-{idx}"
														required
														{...variableAttributes}
													/>
												{:else if variables[variable]?.type === 'month'}
													<input
														type="month"
														class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100 dark:border-gray-850"
														placeholder={variables[variable]?.placeholder ?? ''}
														bind:value={variableValues[variable]}
														autocomplete="off"
														id="input-variable-{idx}"
														required
														{...variableAttributes}
													/>
												{:else if variables[variable]?.type === 'number'}
													<input
														type="number"
														class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100 dark:border-gray-850"
														placeholder={variables[variable]?.placeholder ?? ''}
														bind:value={variableValues[variable]}
														autocomplete="off"
														id="input-variable-{idx}"
														required
														{...variableAttributes}
													/>
												{:else if variables[variable]?.type === 'range'}
													<div class="flex items-center space-x-2">
														<div class="relative flex justify-center items-center gap-2 flex-1">
															<input
																type="range"
																bind:value={variableValues[variable]}
																class="w-full rounded-lg py-1 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100 dark:border-gray-850"
																id="input-variable-{idx}"
																{...variableAttributes}
															/>
														</div>

														<input
															type="text"
															class=" py-1 text-sm dark:text-gray-300 bg-transparent outline-hidden text-right"
															placeholder={$i18n.t('Enter value')}
															bind:value={variableValues[variable]}
															autocomplete="off"
															required
														/>
													</div>

													<!-- <input
														type="range"
														class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100 dark:border-gray-850"
														placeholder={variables[variable]?.placeholder ?? ''}
														bind:value={variableValues[variable]}
														autocomplete="off"
														id="input-variable-{idx}"
														required
													/> -->
												{:else if variables[variable]?.type === 'tel'}
													<input
														type="tel"
														class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100 dark:border-gray-850"
														placeholder={variables[variable]?.placeholder ?? ''}
														bind:value={variableValues[variable]}
														autocomplete="off"
														id="input-variable-{idx}"
														required
														{...variableAttributes}
													/>
												{:else if variables[variable]?.type === 'text'}
													<input
														type="text"
														class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100 dark:border-gray-850"
														placeholder={variables[variable]?.placeholder ?? ''}
														bind:value={variableValues[variable]}
														autocomplete="off"
														id="input-variable-{idx}"
														required
														{...variableAttributes}
													/>
												{:else if variables[variable]?.type === 'time'}
													<input
														type="time"
														class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100 dark:border-gray-850"
														placeholder={variables[variable]?.placeholder ?? ''}
														bind:value={variableValues[variable]}
														autocomplete="off"
														id="input-variable-{idx}"
														required
														{...variableAttributes}
													/>
												{:else if variables[variable]?.type === 'url'}
													<input
														type="url"
														class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100 dark:border-gray-850"
														placeholder={variables[variable]?.placeholder ?? ''}
														bind:value={variableValues[variable]}
														autocomplete="off"
														id="input-variable-{idx}"
														required
														{...variableAttributes}
													/>
												{:else if variables[variable]?.type === 'map'}
													<!-- EXPERIMENTAL INPUT TYPE, DO NOT USE IN PRODUCTION -->
													<div class="flex flex-col items-center gap-1">
														<MapSelector
															setViewLocation={((variableValues[variable] ?? '').includes(',') ??
															false)
																? variableValues[variable].split(',')
																: null}
															onClick={(value) => {
																variableValues[variable] = value;
															}}
														/>

														<input
															type="text"
															class=" w-full py-1 text-left text-sm dark:text-gray-300 bg-transparent outline-hidden"
															placeholder={$i18n.t('Enter coordinates (e.g. 51.505, -0.09)')}
															bind:value={variableValues[variable]}
															autocomplete="off"
															required
														/>
													</div>
												{:else}
													<textarea
														class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100 dark:border-gray-850"
														placeholder={variables[variable]?.placeholder ?? ''}
														bind:value={variableValues[variable]}
														autocomplete="off"
														id="input-variable-{idx}"
														required
													/>
												{/if}
											</div>
										</div>

										<!-- {#if (valvesSpec.properties[property]?.description ?? null) !== null}
									<div class="text-xs text-gray-500">
										{valvesSpec.properties[property].description}
									</div>
								{/if} -->
									</div>
								{/each}
							</div>
						{:else}
							<Spinner className="size-5" />
						{/if}
					</div>

					<div class="flex justify-end pt-3 text-sm font-medium">
						<button
							class="px-3.5 py-1.5 text-sm font-medium bg-white hover:bg-gray-100 text-black dark:bg-black dark:text-white dark:hover:bg-gray-900 transition rounded-full"
							type="button"
							on:click={() => {
								show = false;
							}}
						>
							{$i18n.t('Cancel')}
						</button>

						<button
							class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
							type="submit"
						>
							{$i18n.t('Save')}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>
