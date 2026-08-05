<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import {
		getToolServerUserConfig,
		getToolServerUserConfigSpec,
		updateToolServerUserConfig,
		deleteToolServerUserConfig
	} from '$lib/apis/tools';

	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Valves from '$lib/components/common/Valves.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let serverId: string = '';
	export let serverName: string = '';

	let loading = false;
	let saving = false;

	let valvesSpec: any = null;
	let valves: Record<string, any> = {};
	let config: Record<string, any> = {};

	const initHandler = async () => {
		loading = true;
		valves = {};
		valvesSpec = null;
		config = {};

		try {
			valvesSpec = await getToolServerUserConfigSpec(localStorage.token, serverId);
			config = (await getToolServerUserConfig(localStorage.token, serverId)) ?? {};

			for (const property in valvesSpec?.properties ?? {}) {
				const status = config[property] ?? {};

				// Every field starts as an editable empty string rather than null, so the
				// input is visible right away. Stored secrets are never sent back to the
				// browser: leaving a field empty keeps the stored value, and switching a
				// field to "None" clears that one field.
				valves[property] = status.sensitive ? '' : (status.value ?? '');
			}
		} catch (e) {
			toast.error(`${e}`);
			show = false;
		}

		loading = false;
	};

	const submitHandler = async () => {
		saving = true;

		const res = await updateToolServerUserConfig(localStorage.token, serverId, valves).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		if (res) {
			toast.success($i18n.t('Credentials updated successfully'));
			dispatch('save');
			show = false;
		}

		saving = false;
	};

	const clearHandler = async () => {
		const res = await deleteToolServerUserConfig(localStorage.token, serverId).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Credentials removed successfully'));
			dispatch('save');
			show = false;
		}
	};

	$: if (show && serverId) {
		initHandler();
	}
</script>

<Modal size="sm" bind:show>
	<div>
		<div class="flex justify-between dark:text-gray-100 px-4 pt-3 pb-1">
			<div class="self-center text-sm font-medium">
				{serverName || $i18n.t('Credentials')}
			</div>
			<button
				class="self-center rounded-lg p-1 text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
				aria-label={$i18n.t('Close')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-4'} />
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-4 pb-3 md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div>
						{#if !loading}
							<Valves {valvesSpec} bind:valves />

							<div class="mt-1 text-[0.6875rem] text-gray-400 dark:text-gray-600">
								{$i18n.t(
									'Your credentials are stored for your account only and are never shown again after saving. Leave a field empty to keep the stored value, or switch it to None to remove it.'
								)}
							</div>
						{:else}
							<Spinner className="size-5" />
						{/if}
					</div>

					<div class="flex justify-between items-center pt-2.5 text-sm font-normal">
						<button
							class="px-1 py-1.5 text-sm font-normal text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:underline transition"
							type="button"
							on:click={() => {
								clearHandler();
							}}
						>
							{$i18n.t('Clear')}
						</button>

						<button
							class="px-3 py-1.5 text-sm font-normal bg-black hover:bg-gray-950 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex items-center gap-2 whitespace-nowrap {saving
								? ' cursor-not-allowed'
								: ''}"
							type="submit"
							disabled={saving}
						>
							{$i18n.t('Save')}

							{#if saving}
								<span class="shrink-0">
									<Spinner />
								</span>
							{/if}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>
