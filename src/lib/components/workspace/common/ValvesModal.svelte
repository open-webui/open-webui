<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher } from 'svelte';
	import { onMount, getContext } from 'svelte';
	import { addUser } from '$lib/apis/auths';

	import Modal from '../../common/Modal.svelte';
	import {
		getFunctionValvesById,
		getFunctionValvesSpecById,
		updateFunctionValvesById
	} from '$lib/apis/functions';
	import { getToolValvesById, getToolValvesSpecById, updateToolValvesById } from '$lib/apis/tools';

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

	import Spinner from '../../common/Spinner.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Valves from '$lib/components/common/Valves.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;

	export let type = 'tool';
	export let id = null;
	export let userValves = false;

	let saving = false;
	let loading = false;

	let valvesSpec = null;
	let valves = {};

	const submitHandler = async () => {
		saving = true;

		if (valvesSpec) {
			// Convert string to array
			for (const property in valvesSpec.properties) {
				if (valvesSpec.properties[property]?.type === 'array') {
					if (typeof valves[property] === 'string') {
						valves[property] = (valves[property] ?? '')
							.split(',')
							.map((v) => v.trim())
							.filter((v) => v.length > 0);
					} else if (valves[property] == null) {
						valves[property] = null;
					}
				}
			}

			let res = null;

			if (userValves) {
				if (type === 'tool') {
					res = await updateToolUserValvesById(localStorage.token, id, valves).catch((error) => {
						toast.error(`${error}`);
					});
				} else if (type === 'function') {
					res = await updateFunctionUserValvesById(localStorage.token, id, valves).catch(
						(error) => {
							toast.error(`${error}`);
						}
					);
				}
			} else {
				if (type === 'tool') {
					res = await updateToolValvesById(localStorage.token, id, valves).catch((error) => {
						toast.error(`${error}`);
					});
				} else if (type === 'function') {
					res = await updateFunctionValvesById(localStorage.token, id, valves).catch((error) => {
						toast.error(`${error}`);
					});
				}
			}

			if (res) {
				toast.success($i18n.t('Valves updated successfully'));
				dispatch('save');
			}
		}

		saving = false;
	};

	const initHandler = async () => {
		loading = true;
		valves = {};
		valvesSpec = null;

		try {
			if (userValves) {
				if (type === 'tool') {
					valves = await getToolUserValvesById(localStorage.token, id);
					valvesSpec = await getToolUserValvesSpecById(localStorage.token, id);
				} else if (type === 'function') {
					valves = await getFunctionUserValvesById(localStorage.token, id);
					valvesSpec = await getFunctionUserValvesSpecById(localStorage.token, id);
				}
			} else {
				if (type === 'tool') {
					valves = await getToolValvesById(localStorage.token, id);
					valvesSpec = await getToolValvesSpecById(localStorage.token, id);
				} else if (type === 'function') {
					valves = await getFunctionValvesById(localStorage.token, id);
					valvesSpec = await getFunctionValvesSpecById(localStorage.token, id);
				}
			}

			if (!valves) {
				valves = {};
			}

			if (valvesSpec) {
				for (const property in valvesSpec.properties) {
					if (valvesSpec.properties[property]?.type === 'array') {
						if (valves[property] != null) {
							valves[property] = (Array.isArray(valves[property]) ? valves[property] : []).join(
								','
							);
						} else {
							valves[property] = null;
						}
					}
				}
			}

			loading = false;
		} catch (e) {
			toast.error(`Error fetching valves`);
			show = false;
		}
	};

	$: if (show) {
		initHandler();
	}
</script>

<Modal size="sm" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-2">
			<div class=" text-lg font-medium self-center">{$i18n.t('Valves')}</div>
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
							<Valves {valvesSpec} bind:valves />
						{:else}
							<Spinner className="size-5" />
						{/if}
					</div>

					<div class="flex justify-end pt-3 text-sm font-medium">
						<button
							class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full {saving
								? ' cursor-not-allowed'
								: ''}"
							type="submit"
							disabled={saving}
						>
							{$i18n.t('Save')}

							{#if saving}
								<div class="ml-2 self-center">
									<Spinner />
								</div>
							{/if}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>

<style>
	input::-webkit-outer-spin-button,
	input::-webkit-inner-spin-button {
		/* display: none; <- Crashes Chrome on hover */
		-webkit-appearance: none;
		margin: 0; /* <-- Apparently some margin are still there even though it's hidden */
	}

	.tabs::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.tabs {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
	}

	input[type='number'] {
		-moz-appearance: textfield; /* Firefox */
	}
</style>
