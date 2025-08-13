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
	import Spinner from '../../common/Spinner.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Valves from '$lib/components/common/Valves.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;

	export let type = 'tool';
	export let id = null;

	let saving = false;
	let loading = false;

	let valvesSpec = null;
	let valves = {};
	let pinnedProperties = [];

	const getPinningKey = () => `valve_pins_${type}_${id}`;

	const loadPinnedProperties = () => {
		try {
			const saved = localStorage.getItem(getPinningKey());
			if (saved) {
				pinnedProperties = JSON.parse(saved);
			}
		} catch (error) {
			console.warn('Failed to load pinned properties:', error);
		}
	};

	const savePinnedProperties = () => {
		try {
			localStorage.setItem(getPinningKey(), JSON.stringify(pinnedProperties));
		} catch (error) {
			console.warn('Failed to save pinned properties:', error);
		}
	};

	const submitHandler = async () => {
		saving = true;

		try {
			if (valvesSpec) {
				// Convert string to array only if it's actually a string (for comma-separated values)
				// Multi-select elements already provide arrays, so don't convert those
				for (const property in valvesSpec.properties) {
					if (valvesSpec.properties[property]?.type === 'array') {
						if (typeof valves[property] === 'string') {
							valves[property] = (valves[property] ?? '')
								.split(',')
								.map((v) => v.trim())
								.filter((v) => v);
						}
						// If it's already an array (from multi-select), leave it as is
					}
				}

				let res = null;

				if (type === 'tool') {
					res = await updateToolValvesById(localStorage.token, id, valves);
				} else if (type === 'function') {
					res = await updateFunctionValvesById(localStorage.token, id, valves);
				}

				if (res) {
					toast.success('Valves updated successfully');
					dispatch('save');
				} else {
					toast.error('Failed to update valves');
				}
			}
		} catch (error) {
			console.error('Error updating valves:', error);
			toast.error(`Error: ${error}`);
		} finally {
			saving = false;
		}
	};

	const initHandler = async () => {
		loading = true;
		valves = {};
		valvesSpec = null;

		// Load pinned properties
		loadPinnedProperties();

		if (type === 'tool') {
			valves = await getToolValvesById(localStorage.token, id);
			valvesSpec = await getToolValvesSpecById(localStorage.token, id);
		} else if (type === 'function') {
			valves = await getFunctionValvesById(localStorage.token, id);
			valvesSpec = await getFunctionValvesSpecById(localStorage.token, id);
		}

		if (!valves) {
			valves = {};
		}

		if (valvesSpec) {
			// Convert array to proper format based on input type
			for (const property in valvesSpec.properties) {
				if (valvesSpec.properties[property]?.type === 'array') {
					// For listview (multi-select), keep as array
					// For other array inputs that might be comma-separated, convert to string
					if (valvesSpec.properties[property]?.input?.type === 'listview') {
						// Keep as array for multi-select elements
						if (!Array.isArray(valves[property])) {
							valves[property] = valves[property] ? [valves[property]] : [];
						}
					} else {
						// Convert to comma-separated string for other array types
						valves[property] = (valves[property] ?? []).join(',');
					}
				}
			}
		}

		loading = false;
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
							<Valves
								{valvesSpec}
								bind:valves
								bind:pinnedProperties
								on:pin={savePinnedProperties}
							/>
						{:else}
							<Spinner className="size-5" />
						{/if}
					</div>

					<div class="flex justify-end pt-3 text-sm font-medium">
						<button
							class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition-all duration-200 rounded-full flex items-center space-x-2 {saving
								? ' cursor-not-allowed opacity-80'
								: ''}"
							type="submit"
							disabled={saving}
						>
							<span>{$i18n.t('Save')}</span>

							<div class="loader-container {saving ? 'show' : 'hide'}">
								<Spinner className="size-4" />
							</div>
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

	/* Loader container animations */
	.loader-container {
		overflow: hidden;
		transition: all 0.3s ease-in-out;
		transform-origin: center;
	}

	.loader-container.hide {
		width: 0;
		opacity: 0;
		transform: scale(0);
	}

	.loader-container.show {
		width: 1rem;
		opacity: 1;
		transform: scale(1);
	}
</style>
