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
		class="flex flex-col h-full justify-between space-y-3 text-sm"
		on:submit|preventDefault={() => {
			submitHandler();
			dispatch('save');
		}}
	>
		<div class="flex flex-col">
			<div class="space-y-1">
				<div class="flex gap-2">
					<div class="flex-1">
						<select
							class="  w-full rounded-sm text-xs py-2 px-1 bg-transparent outline-hidden"
							bind:value={tab}
							placeholder={$i18n.t('Select')}
						>
							<option value="tools" class="bg-gray-100 dark:bg-gray-800">{$i18n.t('Tools')}</option>
							<option value="functions" class="bg-gray-100 dark:bg-gray-800"
								>{$i18n.t('Functions')}</option
							>
						</select>
					</div>

					<div class="flex-1">
						<select
							class="w-full rounded-sm py-2 px-1 text-xs bg-transparent outline-hidden"
							bind:value={selectedId}
							on:change={async () => {
								await tick();
							}}
						>
							{#if tab === 'tools'}
								<option value="" selected disabled class="bg-gray-100 dark:bg-gray-800"
									>{$i18n.t('Select a tool')}</option
								>

								{#each $tools
									.filter((tool) => !tool?.id?.startsWith('server:'))
									.sort((a, b) => (a.name ?? '').localeCompare(b.name ?? '')) as tool, toolIdx}
									<option value={tool.id} class="bg-gray-100 dark:bg-gray-800">{tool.name}</option>
								{/each}
							{:else if tab === 'functions'}
								<option value="" selected disabled class="bg-gray-100 dark:bg-gray-800"
									>{$i18n.t('Select a function')}</option
								>

								{#each $functions.sort( (a, b) => (a.name ?? '').localeCompare(b.name ?? '') ) as func, funcIdx}
									<option value={func.id} class="bg-gray-100 dark:bg-gray-800">{func.name}</option>
								{/each}
							{/if}
						</select>
					</div>
				</div>
			</div>

			{#if selectedId}
				<hr class="border-gray-50/30 dark:border-gray-800/30 my-1 w-full" />

				<div class="my-2 text-xs">
					{#if !loading}
						<Valves
							{valvesSpec}
							bind:valves
							on:change={() => {
								debounceSubmitHandler();
							}}
						/>
					{:else}
						<Spinner className="size-5" />
					{/if}
				</div>
			{/if}
		</div>
	</form>
{:else}
	<Spinner className="size-4" />
{/if}
