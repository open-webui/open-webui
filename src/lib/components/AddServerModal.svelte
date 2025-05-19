<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import Modal from '$lib/components/common/Modal.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Minus from '$lib/components/icons/Minus.svelte';
	import PencilSolid from '$lib/components/icons/PencilSolid.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tags from './common/Tags.svelte';
	import { getToolServerData } from '$lib/apis';
	import { verifyToolServerConnection } from '$lib/apis/configs';
	import AccessControl from './workspace/common/AccessControl.svelte';

	export let onSubmit: Function = () => {};
	export let onDelete: Function = () => {};

	export let show = false;
	export let edit = false;

	export let direct = false;

	export let connection = null;

	let url = '';
	let path = 'openapi.json';

	let auth_type = 'bearer';
	let key = '';

	let accessControl = {};

	let enable = true;

	let loading = false;

	const verifyHandler = async () => {
		if (url === '') {
			toast.error($i18n.t('Please enter a valid URL'));
			return;
		}

		if (path === '') {
			toast.error($i18n.t('Please enter a valid path'));
			return;
		}

		if (direct) {
			const res = await getToolServerData(
				auth_type === 'bearer' ? key : localStorage.token,
				`${url}/${path}`
			).catch((err) => {
				toast.error($i18n.t('Connection failed'));
			});

			if (res) {
				toast.success($i18n.t('Connection successful'));
				console.debug('Connection successful', res);
			}
		} else {
			const res = await verifyToolServerConnection(localStorage.token, {
				url,
				path,
				auth_type,
				key,
				config: {
					enable: enable,
					access_control: accessControl
				}
			}).catch((err) => {
				toast.error($i18n.t('Connection failed'));
			});

			if (res) {
				toast.success($i18n.t('Connection successful'));
				console.debug('Connection successful', res);
			}
		}
	};

	const submitHandler = async () => {
		loading = true;

		// remove trailing slash from url
		url = url.replace(/\/$/, '');

		const connection = {
			url,
			path,
			auth_type,
			key,
			config: {
				enable: enable,
				access_control: accessControl
			}
		};

		await onSubmit(connection);

		loading = false;
		show = false;

		url = '';
		path = 'openapi.json';
		key = '';
		auth_type = 'bearer';

		enable = true;
		accessControl = null;
	};

	const init = () => {
		if (connection) {
			url = connection.url;
			path = connection?.path ?? 'openapi.json';

			auth_type = connection?.auth_type ?? 'bearer';
			key = connection?.key ?? '';

			enable = connection.config?.enable ?? true;
			accessControl = connection.config?.access_control ?? null;
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
								<div class="flex justify-between mb-0.5">
									<div class=" text-xs text-gray-500">{$i18n.t('URL')}</div>
								</div>

								<div class="flex flex-1 items-center">
									<input
										class="w-full flex-1 text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
										type="text"
										bind:value={url}
										placeholder={$i18n.t('API Base URL')}
										autocomplete="off"
										required
									/>

									<Tooltip
										content={$i18n.t('Verify Connection')}
										className="shrink-0 flex items-center mr-1"
									>
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

									<Tooltip content={enable ? $i18n.t('Enabled') : $i18n.t('Disabled')}>
										<Switch bind:state={enable} />
									</Tooltip>
								</div>

								<div class="flex-1 flex items-center">
									<div class="text-sm">/</div>
									<input
										class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
										type="text"
										bind:value={path}
										placeholder={$i18n.t('openapi.json Path')}
										autocomplete="off"
										required
									/>
								</div>
							</div>
						</div>

						<div class="text-xs text-gray-500 mt-1">
							{$i18n.t(`WebUI will make requests to "{{url}}"`, {
								url: `${url}/${path}`
							})}
						</div>

						<div class="flex gap-2 mt-2">
							<div class="flex flex-col w-full">
								<div class="  text-xs text-gray-500">{$i18n.t('Auth')}</div>

								<div class="flex gap-2">
									<div class="flex-shrink-0 self-start">
										<select
											class="w-full text-sm bg-transparent dark:bg-gray-900 placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden pr-5"
											bind:value={auth_type}
										>
											<option value="bearer">Bearer</option>
											<option value="session">Session</option>
										</select>
									</div>

									<div class="flex flex-1 items-center">
										{#if auth_type === 'bearer'}
											<SensitiveInput
												className="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
												bind:value={key}
												placeholder={$i18n.t('API Key')}
												required={false}
											/>
										{:else if auth_type === 'session'}
											<div class="text-xs text-gray-500 self-center translate-y-[1px]">
												{$i18n.t('Forwards system user session credentials to authenticate')}
											</div>
										{/if}
									</div>
								</div>
							</div>
						</div>

						{#if !direct}
							<hr class=" border-gray-100 dark:border-gray-700/10 my-2.5 w-full" />

							<div class="my-2 -mx-2">
								<div class="px-3 py-2 bg-gray-50 dark:bg-gray-950 rounded-lg">
									<AccessControl bind:accessControl />
								</div>
							</div>
						{/if}
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
