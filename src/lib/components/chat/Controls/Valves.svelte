<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { config, functions, models, settings, tools, user } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';

	import {
		getUserValvesSpecById as getToolUserValvesSpecById,
		getUserValvesById as getToolUserValvesById,
		updateUserValvesById as updateToolUserValvesById,
		getTools
	} from '$lib/apis/tools';
	import {
		getUserValvesSpecById as getFunctionUserValvesSpecById,
		getUserValvesById as getFunctionUserValvesById,
		updateUserValvesById as updateFunctionUserValvesById,
		getFunctions
	} from '$lib/apis/functions';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Valves from '$lib/components/common/Valves.svelte';

	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	export let show = false;

	let tab = 'tools';
	let selectedId = '';

	let loading = false;

	let valvesSpec = null;
	let valves = {};

	let debounceTimer;

	const debounceSubmitHandler = async () => {
		if (debounceTimer) {
			clearTimeout(debounceTimer);
		}

		// Set a new timer
		debounceTimer = setTimeout(() => {
			submitHandler();
		}, 500); // 0.5 second debounce
	};

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
						toast.error(`${error}`);
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
					toast.error(`${error}`);
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

	$: if (show) {
		init();
	}

	const init = async () => {
		loading = true;

		if ($functions === null) {
			functions.set(await getFunctions(localStorage.token));
		}
		if ($tools === null) {
			tools.set(await getTools(localStorage.token));
		}

		loading = false;
	};
</script>

{#if show && !loading}
	<form
		class="flex flex-col h-full space-y-4 text-sm"
		on:submit|preventDefault={() => {
			submitHandler();
			dispatch('save');
		}}
	>
		<div class="flex flex-col space-y-4">
			<!-- Selection Section -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="space-y-3">
					<!-- Tab Selection -->
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
							{$i18n.t('Type')}
						</label>
						<select
							class="w-full px-3 py-2.5 text-sm bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-colors cursor-pointer"
							bind:value={tab}
							placeholder="Select"
						>
							<option value="tools" class="bg-white dark:bg-gray-700">{$i18n.t('Tools')}</option>
							<option value="functions" class="bg-white dark:bg-gray-700">
								{$i18n.t('Functions')}
							</option>
						</select>
					</div>

					<!-- Item Selection -->
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
							{#if tab === 'tools'}
								{$i18n.t('Select Tool')}
							{:else}
								{$i18n.t('Select Function')}
							{/if}
						</label>
						<select
							class="w-full px-3 py-2.5 text-sm bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
							bind:value={selectedId}
							on:change={async () => {
								await tick();
							}}
						>
							{#if tab === 'tools'}
								<option value="" selected disabled class="bg-white dark:bg-gray-700">
									{$i18n.t('Select a tool')}
								</option>

								{#each $tools as tool, toolIdx}
									<option value={tool.id} class="bg-white dark:bg-gray-700">{tool.name}</option>
								{/each}
							{:else if tab === 'functions'}
								<option value="" selected disabled class="bg-white dark:bg-gray-700">
									{$i18n.t('Select a function')}
								</option>

								{#each $functions as func, funcIdx}
									<option value={func.id} class="bg-white dark:bg-gray-700">{func.name}</option>
								{/each}
							{/if}
						</select>
					</div>
				</div>
			</div>

			<!-- Valves Configuration Section -->
			{#if selectedId}
				<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
					<div class="mb-3">
						<h3 class="text-sm font-semibold text-gray-800 dark:text-gray-200">
							{$i18n.t('Configuration')}
						</h3>
						<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
							{$i18n.t('Adjust the settings below')}
						</p>
					</div>

					<div class="mt-4">
						{#if !loading}
							<Valves
								{valvesSpec}
								bind:valves
								on:change={() => {
									debounceSubmitHandler();
								}}
							/>
						{:else}
							<div class="flex items-center justify-center py-8">
								<Spinner className="size-6" />
							</div>
						{/if}
					</div>
				</div>
			{:else}
				<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-8 border-2 border-dashed border-gray-200 dark:border-gray-700">
					<div class="text-center">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-12 mx-auto text-gray-400 dark:text-gray-500 mb-3"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z"
							/>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
							/>
						</svg>
						<p class="text-sm font-medium text-gray-600 dark:text-gray-400">
							{$i18n.t('No selection')}
						</p>
						<p class="text-xs text-gray-500 dark:text-gray-500 mt-1">
							{$i18n.t('Please select a tool or function to configure')}
						</p>
					</div>
				</div>
			{/if}
		</div>
	</form>
{:else}
	<div class="flex items-center justify-center py-12">
		<Spinner className="size-8" />
	</div>
{/if}