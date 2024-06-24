<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { config, functions, models, settings, tools, user } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';

	import {
		getUserValvesSpecById as getToolUserValvesSpecById,
		getUserValvesById as getToolUserValvesById,
		updateUserValvesById as updateToolUserValvesById
	} from '$lib/apis/tools';
	import {
		getUserValvesSpecById as getFunctionUserValvesSpecById,
		getUserValvesById as getFunctionUserValvesById,
		updateUserValvesById as updateFunctionUserValvesById
	} from '$lib/apis/functions';

	import ManageModal from './Personalization/ManageModal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	export let saveSettings: Function;

	let tab = 'tools';
	let selectedId = '';

	let loading = false;

	let valvesSpec = null;
	let valves = {};

	const getUserValves = async () => {
		loading = true;
		if (tab === 'tools') {
			valves = await getToolUserValvesById(localStorage.token, selectedId);
			valvesSpec = await getToolUserValvesSpecById(localStorage.token, selectedId);
		} else if (tab === 'functions') {
			valves = await getFunctionUserValvesById(localStorage.token, selectedId);
			valvesSpec = await getFunctionUserValvesSpecById(localStorage.token, selectedId);
		}

		if (valvesSpec) {
			// Convert array to string
			for (const property in valvesSpec.properties) {
				if (valvesSpec.properties[property]?.type === 'array') {
					valves[property] = (valves[property] ?? []).join(',');
				}
			}
		}

		loading = false;
	};

	const submitHandler = async () => {
		if (valvesSpec) {
			// Convert string to array
			for (const property in valvesSpec.properties) {
				if (valvesSpec.properties[property]?.type === 'array') {
					valves[property] = (valves[property] ?? '').split(',').map((v) => v.trim());
				}
			}

			if (tab === 'tools') {
				const res = await updateToolUserValvesById(localStorage.token, selectedId, valves).catch(
					(error) => {
						toast.error(error);
						return null;
					}
				);

				if (res) {
					toast.success($i18n.t('Valves updated'));
					valves = res;
				}
			} else if (tab === 'functions') {
				const res = await updateFunctionUserValvesById(
					localStorage.token,
					selectedId,
					valves
				).catch((error) => {
					toast.error(error);
					return null;
				});

				if (res) {
					toast.success($i18n.t('Valves updated'));
					valves = res;
				}
			}
		}
	};

	$: if (tab) {
		selectedId = '';
	}

	$: if (selectedId) {
		getUserValves();
	}
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={() => {
		submitHandler();
		dispatch('save');
	}}
>
	<div class="flex flex-col pr-1.5 overflow-y-scroll max-h-[25rem]">
		<div>
			<div class="flex items-center justify-between mb-2">
				<Tooltip content="">
					<div class="text-sm font-medium">
						{$i18n.t('Manage Valves')}
					</div>
				</Tooltip>

				<div class=" self-end">
					<select
						class=" dark:bg-gray-900 w-fit pr-8 rounded text-xs bg-transparent outline-none text-right"
						bind:value={tab}
						placeholder="Select"
					>
						<option value="tools">{$i18n.t('Tools')}</option>
						<option value="functions">{$i18n.t('Functions')}</option>
					</select>
				</div>
			</div>
		</div>

		<div class="space-y-1">
			<div class="flex gap-2">
				<div class="flex-1">
					<select
						class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
						bind:value={selectedId}
						on:change={async () => {
							await tick();
						}}
					>
						{#if tab === 'tools'}
							<option value="" selected disabled class="bg-gray-100 dark:bg-gray-700"
								>{$i18n.t('Select a tool')}</option
							>

							{#each $tools as tool, toolIdx}
								<option value={tool.id} class="bg-gray-100 dark:bg-gray-700">{tool.name}</option>
							{/each}
						{:else if tab === 'functions'}
							<option value="" selected disabled class="bg-gray-100 dark:bg-gray-700"
								>{$i18n.t('Select a function')}</option
							>

							{#each $functions as func, funcIdx}
								<option value={func.id} class="bg-gray-100 dark:bg-700">{func.name}</option>
							{/each}
						{/if}
					</select>
				</div>
			</div>
		</div>

		{#if selectedId}
			<hr class="dark:border-gray-800 my-3 w-full" />

			<div>
				{#if !loading}
					{#if valvesSpec}
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
										class="p-1 px-3 text-xs flex rounded transition"
										type="button"
										on:click={() => {
											valves[property] = (valves[property] ?? null) === null ? '' : null;
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
									<div class="flex mt-0.5 mb-1.5 space-x-2">
										<div class=" flex-1">
											<input
												class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
												type="text"
												placeholder={valvesSpec.properties[property].title}
												bind:value={valves[property]}
												autocomplete="off"
												required
											/>
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
						<div>No valves</div>
					{/if}
				{:else}
					<Spinner className="size-5" />
				{/if}
			</div>
		{/if}
	</div>

	<div class="flex justify-end text-sm font-medium">
		<button
			class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
