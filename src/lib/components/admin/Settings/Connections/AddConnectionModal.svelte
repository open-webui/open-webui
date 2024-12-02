<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { models } from '$lib/stores';
	import { verifyOpenAIConnection } from '$lib/apis/openai';
	import { verifyOllamaConnection } from '$lib/apis/ollama';

	import Modal from '$lib/components/common/Modal.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Minus from '$lib/components/icons/Minus.svelte';
	import PencilSolid from '$lib/components/icons/PencilSolid.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';

	export let onSubmit: Function = () => {};
	export let onDelete: Function = () => {};

	export let show = false;
	export let edit = false;
	export let ollama = false;

	export let connection = null;

	let url = '';
	let key = '';

	let prefixId = '';
	let enable = true;

	let modelId = '';
	let modelIds = [];

	let loading = false;

	const verifyOllamaHandler = async () => {
		const res = await verifyOllamaConnection(localStorage.token, url, key).catch((error) => {
			toast.error(error);
		});

		if (res) {
			toast.success($i18n.t('Server connection verified'));
		}
	};

	const verifyOpenAIHandler = async () => {
		const res = await verifyOpenAIConnection(localStorage.token, url, key).catch((error) => {
			toast.error(error);
		});

		if (res) {
			toast.success($i18n.t('Server connection verified'));
		}
	};

	const verifyHandler = () => {
		if (ollama) {
			verifyOllamaHandler();
		} else {
			verifyOpenAIHandler();
		}
	};

	const addModelHandler = () => {
		if (modelId) {
			modelIds = [...modelIds, modelId];
			modelId = '';
		}
	};

	const submitHandler = async () => {
		loading = true;

		if (!ollama && (!url || !key)) {
			loading = false;
			toast.error('URL and Key are required');
			return;
		}

		const connection = {
			url,
			key,
			config: {
				enable: enable,
				prefix_id: prefixId,
				model_ids: modelIds
			}
		};

		await onSubmit(connection);

		loading = false;
		show = false;

		url = '';
		key = '';
		prefixId = '';
		modelIds = [];
	};

	const init = () => {
		if (connection) {
			url = connection.url;
			key = connection.key;

			enable = connection.config?.enable ?? true;
			prefixId = connection.config?.prefix_id ?? '';
			modelIds = connection.config?.model_ids ?? [];
		}
	};

	$: if (show) {
		init();
	}

	onMount(() => {
		init();
	});
</script>

<Modal size="sm" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-100 px-5 pt-4 pb-2">
			<div class=" text-lg font-medium self-center font-primary">
				{#if edit}
					{$i18n.t('Edit Connection')}
				{:else}
					{$i18n.t('Add Connection')}
				{/if}
			</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-4 pb-4 md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full"
					on:submit={(e) => {
						e.preventDefault();
						submitHandler();
					}}
				>
					<div class="px-1">
						<div class="flex gap-2">
							<div class="flex flex-col w-full">
								<div class=" mb-0.5 text-xs text-gray-500">{$i18n.t('URL')}</div>

								<div class="flex-1">
									<input
										class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-none"
										type="text"
										bind:value={url}
										placeholder={$i18n.t('API Base URL')}
										autocomplete="off"
										required
									/>
								</div>
							</div>

							<Tooltip content="Verify Connection" className="self-end -mb-1">
								<button
									class="self-center p-1 bg-transparent hover:bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-850 rounded-lg transition"
									on:click={() => {
										verifyHandler();
									}}
									type="button"
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
							</Tooltip>

							<div class="flex flex-col flex-shrink-0 self-end">
								<Tooltip content={enable ? $i18n.t('Enabled') : $i18n.t('Disabled')}>
									<Switch bind:state={enable} />
								</Tooltip>
							</div>
						</div>

						<div class="flex gap-2 mt-2">
							<div class="flex flex-col w-full">
								<div class=" mb-0.5 text-xs text-gray-500">{$i18n.t('Key')}</div>

								<div class="flex-1">
									<SensitiveInput
										className="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-none"
										bind:value={key}
										placeholder={$i18n.t('API Key')}
										required={!ollama}
									/>
								</div>
							</div>

							<div class="flex flex-col w-full">
								<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Prefix ID')}</div>

								<div class="flex-1">
									<Tooltip
										content={$i18n.t(
											'Prefix ID is used to avoid conflicts with other connections by adding a prefix to the model IDs - leave empty to disable'
										)}
									>
										<input
											class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-none"
											type="text"
											bind:value={prefixId}
											placeholder={$i18n.t('Prefix ID')}
											autocomplete="off"
										/>
									</Tooltip>
								</div>
							</div>
						</div>

						<hr class=" border-gray-100 dark:border-gray-700/10 my-2.5 w-full" />

						<div class="flex flex-col w-full">
							<div class="mb-1 flex justify-between">
								<div class="text-xs text-gray-500">{$i18n.t('Model IDs')}</div>
							</div>

							{#if modelIds.length > 0}
								<div class="flex flex-col">
									{#each modelIds as modelId, modelIdx}
										<div class=" flex gap-2 w-full justify-between items-center">
											<div class=" text-sm flex-1 py-1 rounded-lg">
												{modelId}
											</div>
											<div class="flex-shrink-0">
												<button
													type="button"
													on:click={() => {
														modelIds = modelIds.filter((_, idx) => idx !== modelIdx);
													}}
												>
													<Minus strokeWidth="2" className="size-3.5" />
												</button>
											</div>
										</div>
									{/each}
								</div>
							{:else}
								<div class="text-gray-500 text-xs text-center py-2 px-10">
									{#if ollama}
										{$i18n.t('Leave empty to include all models from "{{URL}}/api/tags" endpoint', {
											URL: url
										})}
									{:else}
										{$i18n.t('Leave empty to include all models from "{{URL}}/models" endpoint', {
											URL: url
										})}
									{/if}
								</div>
							{/if}
						</div>

						<hr class=" border-gray-100 dark:border-gray-700/10 my-2.5 w-full" />

						<div class="flex items-center">
							<input
								class="w-full py-1 text-sm rounded-lg bg-transparent {modelId
									? ''
									: 'text-gray-500'} placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-none"
								bind:value={modelId}
								placeholder={$i18n.t('Add a model ID')}
							/>

							<div>
								<button
									type="button"
									on:click={() => {
										addModelHandler();
									}}
								>
									<Plus className="size-3.5" strokeWidth="2" />
								</button>
							</div>
						</div>
					</div>

					<div class="flex justify-end pt-3 text-sm font-medium gap-1.5">
						{#if edit}
							<button
								class="px-3.5 py-1.5 text-sm font-medium dark:bg-black dark:hover:bg-gray-900 dark:text-white bg-white text-black hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center"
								type="button"
								on:click={() => {
									onDelete();
									show = false;
								}}
							>
								{$i18n.t('Delete')}
							</button>
						{/if}

						<button
							class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center {loading
								? ' cursor-not-allowed'
								: ''}"
							type="submit"
							disabled={loading}
						>
							{$i18n.t('Save')}

							{#if loading}
								<div class="ml-2 self-center">
									<svg
										class=" w-4 h-4"
										viewBox="0 0 24 24"
										fill="currentColor"
										xmlns="http://www.w3.org/2000/svg"
										><style>
											.spinner_ajPY {
												transform-origin: center;
												animation: spinner_AtaB 0.75s infinite linear;
											}
											@keyframes spinner_AtaB {
												100% {
													transform: rotate(360deg);
												}
											}
										</style><path
											d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z"
											opacity=".25"
										/><path
											d="M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z"
											class="spinner_ajPY"
										/></svg
									>
								</div>
							{/if}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>
