<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { settings } from '$lib/stores';

	import Modal from '$lib/components/common/Modal.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import AccessControlModal from '$lib/components/workspace/common/AccessControlModal.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { getToolServerData } from '$lib/apis';

	export let show = false;
	export let edit = false;
	export let admin = false;
	export let connection = null;

	export let onSubmit: Function = () => {};
	export let onDelete: () => void = () => {};

	let url = '';
	let key = '';
	let name = '';
	let id = '';
	let auth_type = 'bearer';
	let path = '/openapi.json';
	let enabled = false;
	let showAdvanced = false;
	let showAccessControlModal = false;
	let accessGrants: any[] = [];
	let verifying = false;

	const verifyHandler = async () => {
		if (url === '') {
			toast.error($i18n.t('Please enter a valid URL'));
			return;
		}

		if (path === '') {
			toast.error($i18n.t('Please enter a valid path'));
			return;
		}

		// Validate API key is provided when auth_type is bearer
		if (auth_type === 'bearer' && !key.trim()) {
			toast.error($i18n.t('API Key is required for Bearer authentication'));
			return;
		}

		verifying = true;
		try {
			const terminalUrl = url.replace(/\/$/, '');

			// Build authentication headers
			const headers: Record<string, string> = {
				Accept: 'application/json',
				'Content-Type': 'application/json'
			};

			if (auth_type === 'bearer') {
				if (!key.trim()) {
					throw new Error($i18n.t('API Key is required for Bearer authentication'));
				}
				headers['Authorization'] = `Bearer ${key}`;
			} else if (auth_type === 'session') {
				headers['Authorization'] = `Bearer ${localStorage.token}`;
			}

			// Test 1: Try to get OpenAPI spec first (basic connectivity check)
			const requestUrl = path.includes('://')
				? path
				: `${terminalUrl}${path.startsWith('/') ? '' : '/'}${path}`;
			const specResponse = await fetch(requestUrl, {
				method: 'GET',
				headers
			});

			if (!specResponse.ok) {
				// Try to get error details
				let errorMessage = 'Failed to connect to terminal server';
				try {
					const errorData = await specResponse.json();
					if (errorData.detail) {
						errorMessage = errorData.detail;
					} else if (errorData.error) {
						errorMessage = errorData.error;
					} else if (errorData.message) {
						errorMessage = errorData.message;
					}
				} catch (e) {
					// If response is not JSON, use status text
					errorMessage = specResponse.statusText || errorMessage;
				}
				throw new Error(errorMessage);
			}

			// Verify we got valid OpenAPI spec
			const specData = await specResponse.json();
			if (!specData || !specData.paths) {
				throw new Error($i18n.t('Invalid OpenAPI spec received'));
			}

			// Test 2: Call a real terminal endpoint that requires authentication
			// Try /browse/ endpoint first (most common)
			const browseUrl = `${terminalUrl}/browse/`;
			let authValid = false;

			try {
				const browseResponse = await fetch(browseUrl, {
					method: 'GET',
					headers
				});

				// Check for authentication errors
				if (browseResponse.status === 401 || browseResponse.status === 403) {
					throw new Error($i18n.t('Invalid API Key or authentication failed'));
				}

				// If we got a successful response (2xx), authentication is valid
				if (browseResponse.ok) {
					authValid = true;
				}
			} catch (e) {
				// If /browse/ doesn't exist or fails, try other endpoints
				console.warn('Browse endpoint not available, trying alternatives');
			}

			// Test 3: Try /info endpoint if browse failed
			if (!authValid) {
				try {
					const infoResponse = await fetch(`${terminalUrl}/info`, {
						method: 'GET',
						headers
					});

					if (infoResponse.status === 401 || infoResponse.status === 403) {
						throw new Error($i18n.t('Invalid API Key or authentication failed'));
					}

					if (infoResponse.ok) {
						authValid = true;
					}
				} catch (e) {
					console.warn('Info endpoint not available');
				}
			}

			// Test 4: Try a simple command execution test
			if (!authValid) {
				try {
					// Try to execute a simple command to test authentication
					const commandResponse = await fetch(`${terminalUrl}/execute`, {
						method: 'POST',
						headers,
						body: JSON.stringify({
							command: 'pwd',
							cwd: '/'
						})
					});

					if (commandResponse.status === 401 || commandResponse.status === 403) {
						throw new Error($i18n.t('Invalid API Key or authentication failed'));
					}

					if (commandResponse.ok) {
						authValid = true;
					}
				} catch (e) {
					console.warn('Command endpoint not available');
				}
			}

			// If we couldn't verify authentication through any real endpoint,
			// but the OpenAPI spec is accessible, we can't guarantee API key validity
			// We should warn the user about this limitation
			if (!authValid) {
				console.warn(
					'Could not fully validate API key - no authentication-required endpoints found'
				);
				toast.warning(
					$i18n.t(
						'OpenAPI spec is accessible, but API key validity could not be verified. Test by using the terminal.'
					)
				);
			} else {
				toast.success($i18n.t('Connection successful'));
			}

			console.debug('Connection verified', { specData, authValid });
		} catch (error) {
			console.error('Verification error:', error);
			const errorMessage = error.message || $i18n.t('Connection failed');

			// Provide more specific error messages
			if (
				errorMessage.includes('401') ||
				errorMessage.includes('403') ||
				errorMessage.toLowerCase().includes('invalid') ||
				errorMessage.toLowerCase().includes('authentication')
			) {
				toast.error($i18n.t('Invalid API Key or authentication failed'));
			} else if (
				errorMessage.includes('Network') ||
				errorMessage.includes('fetch') ||
				errorMessage.includes('ECONNREFUSED') ||
				errorMessage.includes('Failed to fetch')
			) {
				toast.error($i18n.t('Failed to connect to terminal server'));
			} else {
				toast.error(errorMessage);
			}
		} finally {
			verifying = false;
		}
	};

	const init = () => {
		if (connection) {
			id = connection?.id ?? '';
			url = connection.url;
			key = connection?.key ?? '';
			name = connection?.name ?? '';
			auth_type = connection?.auth_type ?? 'bearer';
			path = connection?.path ?? '/openapi.json';
			enabled = connection?.enabled ?? true;
			accessGrants = connection?.config?.access_grants ?? [];
		} else {
			id = '';
			url = '';
			key = '';
			name = '';
			auth_type = 'bearer';
			path = '/openapi.json';
			enabled = false;
			accessGrants = [];
		}
	};

	$: if (show) {
		init();
	}

	const submitHandler = () => {
		if (url === '') {
			toast.error($i18n.t('Please enter a valid URL'));
			return;
		}

		// Remove trailing slash
		url = url.replace(/\/$/, '');

		const result = {
			...(admin && id.trim() ? { id: id.trim() } : {}),
			url,
			key,
			name,
			path,
			auth_type,
			enabled: enabled,
			config: {
				...(admin ? { access_grants: accessGrants } : {})
			}
		};

		onSubmit(result);
		show = false;
	};
</script>

<Modal size="sm" bind:show>
	<div>
		<div class="flex justify-between dark:text-gray-100 px-5 pt-4 pb-2">
			<h1 class="text-lg font-medium self-center font-primary">
				{#if edit}
					{$i18n.t('Edit Terminal Connection')}
				{:else}
					{$i18n.t('Add Terminal Connection')}
				{/if}
			</h1>

			<button
				class="self-center"
				aria-label={$i18n.t('Close')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-4 pb-4 md:space-x-4 dark:text-gray-200">
			<div class="flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form class="flex flex-col w-full" on:submit|preventDefault={submitHandler}>
					<div class="px-1">
						<div class="flex gap-2">
							<div class="flex flex-col flex-1">
								<div class="flex justify-between mb-0.5">
									<label
										for="terminal-name"
										class={`text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
										>{$i18n.t('Name')}</label
									>
								</div>

								<div class="flex flex-1 items-center">
									<input
										id="terminal-name"
										class={`w-full flex-1 text-sm bg-transparent ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
										type="text"
										bind:value={name}
										placeholder={$i18n.t('My Terminal')}
										autocomplete="off"
									/>
								</div>
							</div>
							{#if admin}
								<div class="flex flex-col flex-1">
									<div class="flex justify-between mb-0.5">
										<label
											for="terminal-id"
											class={`text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
											>{$i18n.t('ID')}
											<span class="opacity-50">({$i18n.t('optional')})</span></label
										>
									</div>
									<div class="flex flex-1 items-center">
										<input
											id="terminal-id"
											class={`w-full flex-1 text-sm bg-transparent font-mono ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
											type="text"
											bind:value={id}
											placeholder="auto"
											autocomplete="off"
										/>
									</div>
								</div>
							{/if}
						</div>

						<div class="flex gap-2 mt-2">
							<div class="flex flex-col w-full">
								<div class="flex justify-between mb-0.5">
									<label
										for="terminal-url"
										class={`text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
										>{$i18n.t('URL')}</label
									>
								</div>

								<div class="flex flex-1 items-center">
									<input
										id="terminal-url"
										class={`w-full flex-1 text-sm bg-transparent ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
										type="text"
										bind:value={url}
										placeholder="http://localhost:9900"
										required
										autocomplete="off"
									/>

									<Tooltip
										content={$i18n.t('Verify Connection')}
										className="shrink-0 flex items-center mr-1"
									>
										<button
											class="self-center p-1 bg-transparent hover:bg-gray-100 dark:hover:bg-gray-850 rounded-lg transition"
											on:click={() => {
												verifyHandler();
											}}
											aria-label={$i18n.t('Verify Connection')}
											type="button"
											disabled={verifying}
										>
											{#if verifying}
												<Spinner className="w-4 h-4" />
											{:else}
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
											{/if}
										</button>
									</Tooltip>
								</div>
							</div>
						</div>

						<div class="flex items-center justify-between">
							<button
								type="button"
								class="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition mt-2"
								on:click={() => (showAdvanced = !showAdvanced)}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									class="w-3 h-3 transition-transform {showAdvanced ? 'rotate-90' : ''}"
								>
									<path
										fill-rule="evenodd"
										d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
										clip-rule="evenodd"
									/>
								</svg>
								{$i18n.t('Advanced')}
							</button>

							{#if admin}
								<button
									class="bg-gray-50 hover:bg-gray-100 text-black dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white transition px-2 py-1 object-cover rounded-full flex gap-1 items-center mt-2"
									type="button"
									on:click={() => {
										showAccessControlModal = true;
									}}
								>
									<LockClosed strokeWidth="2.5" className="size-3.5 shrink-0" />

									<div class="text-xs font-medium shrink-0">
										{$i18n.t('Access')}
									</div>
								</button>
							{/if}
						</div>

						{#if showAdvanced}
							<div class="flex gap-2 mt-2">
								<div class="flex flex-col w-full">
									<div class="flex justify-between items-center mb-0.5">
										<div class="flex gap-2 items-center">
											<div
												class={`text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
											>
												{$i18n.t('OpenAPI Spec')}
											</div>
										</div>
									</div>

									<div class="flex gap-2">
										<div class="flex flex-1 items-center">
											<div class="flex-1 flex items-center">
												<label for="openapi-path" class="sr-only"
													>{$i18n.t('openapi.json URL or Path')}</label
												>
												<input
													class={`w-full text-sm bg-transparent ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
													type="text"
													id="openapi-path"
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
											url: path.includes('://')
												? path
												: `${url}${path.startsWith('/') ? '' : '/'}${path}`
										})}
									</div>
								</div>
							</div>
						{/if}

						<div class="flex gap-2 mt-2">
							<div class="flex flex-col w-full">
								<div class="flex justify-between items-center">
									<div class="flex gap-2 items-center">
										<div
											class={`text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
										>
											{$i18n.t('Auth')}
										</div>
									</div>
								</div>

								<div class="flex gap-2">
									<div class="flex-shrink-0 self-start">
										<select
											class={`dark:bg-gray-900 w-full text-sm bg-transparent pr-5 ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
											bind:value={auth_type}
										>
											<option value="none">{$i18n.t('None')}</option>
											<option value="bearer">{$i18n.t('Bearer')}</option>
											{#if admin}
												<option value="session">{$i18n.t('Session')}</option>
												<option value="system_oauth">{$i18n.t('OAuth')}</option>
											{/if}
										</select>
									</div>

									<div class="flex flex-1 items-center">
										{#if auth_type === 'bearer'}
											<SensitiveInput
												bind:value={key}
												placeholder={$i18n.t('API Key')}
												required={false}
											/>
										{:else if auth_type === 'none'}
											<div
												class={`text-xs self-center translate-y-[1px] ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
											>
												{$i18n.t('No authentication')}
											</div>
										{:else if auth_type === 'session'}
											<div
												class={`text-xs self-center translate-y-[1px] ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
											>
												{$i18n.t('Forwards system user session credentials to authenticate')}
											</div>
										{:else if auth_type === 'system_oauth'}
											<div
												class={`text-xs self-center translate-y-[1px] ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
											>
												{$i18n.t('Forwards system user OAuth access token to authenticate')}
											</div>
										{/if}
									</div>
								</div>
							</div>
						</div>

						<div class="flex justify-between pt-3 text-sm font-medium gap-1.5">
							<div></div>
							<div class="flex gap-1.5">
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
									class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center"
									type="submit"
								>
									{$i18n.t('Save')}
								</button>
							</div>
						</div>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>

<AccessControlModal bind:show={showAccessControlModal} bind:accessGrants />
