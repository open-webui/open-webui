<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onDestroy, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { settings } from '$lib/stores';
	import Modal from '$lib/components/common/Modal.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Minus from '$lib/components/icons/Minus.svelte';
	import PencilSolid from '$lib/components/icons/PencilSolid.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tags from './common/Tags.svelte';
	import { getToolServerData, getToolServerOAuthProviders } from '$lib/apis';
	import { verifyToolServerConnection } from '$lib/apis/configs';
	import AccessControl from './workspace/common/AccessControl.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	import { WEBUI_BASE_URL } from '$lib/constants';
  
	export let onSubmit: Function = () => {};
	export let onDelete: Function = () => {};

	export let show = false;
	export let edit = false;

	export let direct = false;
	export let connection = null;

	let url = '';
	let path = 'openapi.json';

	let auth_type = 'bearer';
	let oAuthProviders: string[] = [];
	let oAuthProvider = '';
	let bearerKey = '';

	let oAuthAccessToken = '';

	let popup: WindowProxy | null = null;

	let accessControl = {};

	let name = '';
	let description = '';

	let enable = true;

	let loading = false;

	const startOAuthFlow = async () => {
		// Idea: Pass the server_url and do whole OAuth login + Verify Connection flow?
		const loginUrl = `${WEBUI_BASE_URL}/toolserver/${oAuthProvider}/login`;

		popup = window.open(
			loginUrl,
			'oauthPopup',
			'width=500,height=600'
		);
	};

	const verifyHandler = async () => {
		if (url === '') {
			toast.error($i18n.t('Please enter a valid URL'));
			return;
		}

		if (path === '') {
			toast.error($i18n.t('Please enter a valid path'));
			return;
		}

		if (auth_type === 'oauth' && oAuthAccessToken === '') {
			toast.error($i18n.t('Please Sign In to your selected provider, or manually enter an Access Token.'));
			return;
		}

		const key = auth_type === 'oauth' ? oAuthAccessToken : auth_type === 'bearer' ? bearerKey : localStorage.token;

		if (direct) {
			const res = await getToolServerData(
				key,
				path.includes('://') ? path : `${url}${path.startsWith('/') ? '' : '/'}${path}`,
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
				},
				info: {
					name,
					description
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
		const key = auth_type === 'oauth' ? oAuthAccessToken : auth_type === 'bearer' ? bearerKey : localStorage.token;
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
			},
			info: {
				name: name,
				description: description
			}
		};

		await onSubmit(connection);

		loading = false;
		show = false;

		url = '';
		path = 'openapi.json';
		bearerKey = '';
		oAuthAccessToken = '';
		auth_type = 'bearer';

		name = '';
		description = '';

		enable = true;
		accessControl = null;
	};

	const init = () => {
		if (connection) {
			url = connection.url;
			path = connection?.path ?? 'openapi.json';

			auth_type = connection?.auth_type ?? 'bearer';
			bearerKey = connection?.key ?? '';
			oAuthAccessToken = connection?.key ?? '';

			name = connection.info?.name ?? '';
			description = connection.info?.description ?? '';

			enable = connection.config?.enable ?? true;
			accessControl = connection.config?.access_control ?? null;
		}

		getToolServerOAuthProviders().then((providers) => {
			if (providers.length > 0) {
				oAuthProviders = providers;
				oAuthProvider = oAuthProviders[0];
			}
		});
	};

	$: if (show) {
		init();
	}

	let handleOAuthMessage: (event: MessageEvent, connection: any) => void;

	onMount(() => {
		handleOAuthMessage = (event: MessageEvent, connection: any) => {
			if (event.origin !== WEBUI_BASE_URL) return;

			const data = event.data;

			try {
				if (data.toolserverAuthSuccess && connection) {
					oAuthAccessToken = data.accessToken;
					connection.key = data.accessToken;
					onSubmit(connection);
					toast.success($i18n.t(`Authentication successful! Access token was set.`));
					if (popup) popup.close();
				} else {
					toast.error($i18n.t(`Failed to authenticate to ${data.provider}`));
				}
			} catch (e: any) {
				toast.error($i18n.t(`Failed to process authentication response: ${e.message}`));
			}
		};
		window.addEventListener('message', (event: MessageEvent) => handleOAuthMessage(event, connection));
		init();
	});

	onDestroy(() => {
		window.removeEventListener('message', (event: MessageEvent) => handleOAuthMessage(event, connection));
	});
</script>

<Modal size="sm" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-100 px-5 pt-4 pb-2">
			<h1 class=" text-lg font-medium self-center font-primary">
				{#if edit}
					{$i18n.t('Edit Connection')}
				{:else}
					{$i18n.t('Add Connection')}
				{/if}
			</h1>
			<button
				class="self-center"
				aria-label={$i18n.t('Close Configure Connection Modal')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
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
									<label
										for="api-base-url"
										class={`text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
										>{$i18n.t('URL')}</label
									>
								</div>

								<div class="flex flex-1 items-center">
									<input
										id="api-base-url"
										class={`w-full flex-1 text-sm bg-transparent ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
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
											aria-label={$i18n.t('Verify Connection')}
											type="button"
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 20 20"
												fill="currentColor"
												class="w-4 h-4"
												aria-hidden="true"
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
									<label for="url-or-path" class="sr-only"
										>{$i18n.t('openapi.json URL or Path')}</label
									>
									<input
										class={`w-full text-sm bg-transparent ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
										type="text"
										id="url-or-path"
										bind:value={path}
										placeholder={$i18n.t('openapi.json URL or Path')}
										autocomplete="off"
										required
									/>
								</div>
							</div>
						</div>

						<div
							class={`text-xs mt-1 ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
						>
							{$i18n.t(`WebUI will make requests to "{{url}}"`, {
								url: path.includes('://') ? path : `${url}${path.startsWith('/') ? '' : '/'}${path}`
							})}
						</div>

						<div class="flex gap-2 mt-2">
							<div class="flex flex-col w-full">
								<div class="text-xs text-gray-500">{$i18n.t('Auth')}</div>
								<label
									for="select-bearer-or-session"
									class={`text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
									>{$i18n.t('Auth')}</label
								>

								<div class="flex items-center gap-2">
									<div class="flex-shrink-0">
										<select
											id="select-bearer-or-session"
											class={`w-full text-sm bg-transparent pr-5 ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
											bind:value={auth_type}
										>
											<option value="bearer">Bearer</option>
											<option value="session">Session</option>
											<option value="oauth">OAuth</option>
										</select>
									</div>

									{#if auth_type === 'oauth'}
										<div class="flex-shrink-0">
											{#if oAuthProviders.length === 0}
												<div class="text-xs text-gray-500 self-center translate-y-[1px]">
													{$i18n.t('No OAuth providers configured. Please contact your administrator.')}
												</div>
											{:else}
											<select
												class="w-full text-sm bg-transparent dark:bg-gray-900 placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden pr-5"
												bind:value={oAuthProvider}
											>
												{#each oAuthProviders as provider}
													<option value={provider}>{provider.charAt(0).toUpperCase() + provider.slice(1)}</option>
												{/each}
											</select>
											{/if}
										</div>
									{/if}
									<div class="flex-1">
										{#if auth_type === 'bearer'}
											<SensitiveInput
												className="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
												bind:value={bearerKey}
												placeholder={$i18n.t('API Key')}
												required={false}
											/>
										{:else if auth_type === 'session'}
											<div
												class={`text-xs self-center translate-y-[1px] ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
											>
												{$i18n.t('Forwards system user session credentials to authenticate')}
											</div>
										{:else if auth_type === 'oauth' && oAuthProvider !== ''}
											<button
												class="ml-auto px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center"
												on:click={() => startOAuthFlow()}
											>
												{$i18n.t(oAuthAccessToken === '' ? 'Sign In' : 'Refresh Token')}
											</button>
										{/if}
									</div>
								</div>

								{#if auth_type === 'oauth'}
									<div class="mt-2">
										<div class="text-xs text-gray-500 self-center translate-y-[1px]">
											{$i18n.t('OAuth Access Token')}
										</div>
										<SensitiveInput
											className="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
											bind:value={oAuthAccessToken}
											placeholder={$i18n.t('OAuth Access Token')}
											required={true}
										/>
									</div>
								{/if}
							</div>
						</div>

						{#if !direct}
							<hr class=" border-gray-100 dark:border-gray-700/10 my-2.5 w-full" />

							<div class="flex gap-2">
								<div class="flex flex-col w-full">
									<label
										for="enter-name"
										class={`mb-0.5 text-xs" ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
										>{$i18n.t('Name')}</label
									>

									<div class="flex-1">
										<input
											id="enter-name"
											class={`w-full text-sm bg-transparent ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
											type="text"
											bind:value={name}
											placeholder={$i18n.t('Enter name')}
											autocomplete="off"
											required
										/>
									</div>
								</div>
							</div>

							<div class="flex flex-col w-full mt-2">
								<label
									for="description"
									class={`mb-1 text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100 placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700 text-gray-500'}`}
									>{$i18n.t('Description')}</label
								>

								<div class="flex-1">
									<input
										id="description"
										class={`w-full text-sm bg-transparent ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
										type="text"
										bind:value={description}
										placeholder={$i18n.t('Enter description')}
										autocomplete="off"
									/>
								</div>
							</div>

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
