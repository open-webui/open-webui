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
	let enabled = true;
	let showAdvanced = false;
	let showAccessControlModal = false;
	let accessGrants: any[] = [];

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
			enabled = true;
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
										>{$i18n.t('ID')} <span class="opacity-50">({$i18n.t('optional')})</span></label>
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
