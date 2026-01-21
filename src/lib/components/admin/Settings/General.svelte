<script lang="ts">
	import DOMPurify from 'dompurify';

	import { getVersionUpdates, getWebhookUrl, updateWebhookUrl } from '$lib/apis';
	import {
		getAdminConfig,
		getLdapConfig,
		getLdapServer,
		updateAdminConfig,
		updateLdapConfig,
		updateLdapServer
	} from '$lib/apis/auths';
	import { getGroups } from '$lib/apis/groups';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { WEBUI_BUILD_HASH, WEBUI_VERSION } from '$lib/constants';
	import { config, showChangelog, versionUpdatesCache, adminConfigCache, webhookUrlCache, groupsCache, ldapServerCache, ldapConfigCache } from '$lib/stores';
	import { compareVersion } from '$lib/utils';
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Textarea from '$lib/components/common/Textarea.svelte';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let updateAvailable = null;
	let version = {
		current: '',
		latest: ''
	};

	let adminConfig = null;
	let webhookUrl = '';
	let groups = [];

	// LDAP
	let ENABLE_LDAP = false;
	let LDAP_SERVER = {
		label: '',
		host: '',
		port: '',
		attribute_for_mail: 'mail',
		attribute_for_username: 'uid',
		app_dn: '',
		app_dn_password: '',
		search_base: '',
		search_filters: '',
		use_tls: false,
		certificate_path: '',
		ciphers: ''
	};

	const checkForVersionUpdates = async () => {
		updateAvailable = null;
		// Use cached version if available
		if ($versionUpdatesCache) {
			version = $versionUpdatesCache;
			updateAvailable = compareVersion(version.latest, version.current);
			return;
		}
		version = await getVersionUpdates(localStorage.token).catch((error) => {
			return {
				current: WEBUI_VERSION,
				latest: WEBUI_VERSION
			};
		});

		console.info(version);
		// Cache the result
		versionUpdatesCache.set(version);

		updateAvailable = compareVersion(version.latest, version.current);
		console.info(updateAvailable);
	};

	const updateLdapServerHandler = async () => {
		if (!ENABLE_LDAP) return;
		const res = await updateLdapServer(localStorage.token, LDAP_SERVER).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (res) {
			toast.success($i18n.t('LDAP server updated'));
		}
	};

	const updateHandler = async () => {
		webhookUrl = await updateWebhookUrl(localStorage.token, webhookUrl);
		webhookUrlCache.set(webhookUrl);
		const res = await updateAdminConfig(localStorage.token, adminConfig);
		if (res) {
			adminConfigCache.set(adminConfig);
		}
		await updateLdapConfig(localStorage.token, ENABLE_LDAP);
		ldapConfigCache.set({ ENABLE_LDAP });
		await updateLdapServerHandler();
		if (LDAP_SERVER) {
			ldapServerCache.set(LDAP_SERVER);
		}

		if (res) {
			saveHandler();
		} else {
			toast.error($i18n.t('Failed to update settings'));
		}
	};

	onMount(async () => {
		if ($config?.features?.enable_version_update_check) {
			checkForVersionUpdates();
		}

		await Promise.all([
			(async () => {
				if ($adminConfigCache) {
					adminConfig = JSON.parse(JSON.stringify($adminConfigCache));
				} else {
					adminConfig = await getAdminConfig(localStorage.token);
					adminConfigCache.set(adminConfig);
				}
			})(),

			(async () => {
				if ($webhookUrlCache !== null) {
					webhookUrl = $webhookUrlCache;
				} else {
					webhookUrl = await getWebhookUrl(localStorage.token);
					webhookUrlCache.set(webhookUrl);
				}
			})(),
			(async () => {
				if ($ldapServerCache) {
					LDAP_SERVER = JSON.parse(JSON.stringify($ldapServerCache));
				} else {
					LDAP_SERVER = await getLdapServer(localStorage.token);
					ldapServerCache.set(LDAP_SERVER);
				}
			})(),
			(async () => {
				if ($groupsCache) {
					groups = $groupsCache;
				} else {
					groups = await getGroups(localStorage.token);
					groupsCache.set(groups);
				}
			})()
		]);

		if ($ldapConfigCache !== null) {
			ENABLE_LDAP = $ldapConfigCache.ENABLE_LDAP;
		} else {
			const ldapConfig = await getLdapConfig(localStorage.token);
			ldapConfigCache.set(ldapConfig);
			ENABLE_LDAP = ldapConfig.ENABLE_LDAP;
		}
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={async () => {
		updateHandler();
	}}
>
	<div class="space-y-4 overflow-y-scroll scrollbar-hidden h-full pr-2">
		{#if adminConfig !== null}
			<div class="max-w-5xl mx-auto">
				<div class="mb-3.5">
					<div class=" mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('General')}</div>

					<hr class="border-gray-100/30 dark:border-gray-850/30 my-2" />

					<div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
						<div
							class="bg-gray-50 dark:bg-gray-850 rounded-lg p-4 flex flex-col justify-between border border-gray-100 dark:border-gray-800"
						>
							<div>
								<div class="text-xs font-medium text-gray-500 mb-2">{$i18n.t('Version')}</div>
								<div class="flex items-center gap-2 mb-4">
									<div class="text-3xl font-bold font-primary text-gray-800 dark:text-gray-100">
										v{WEBUI_VERSION}
									</div>
									<Tooltip content={WEBUI_BUILD_HASH}>
										<span
											class="text-xs text-gray-400 font-mono tracking-wider bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded-md"
										>
											{WEBUI_BUILD_HASH.substring(0, 7)}
										</span>
									</Tooltip>
								</div>
							</div>

							<div class="flex flex-col gap-2">
								{#if $config?.features?.enable_version_update_check}
									<button
										class="w-full text-center px-4 py-2 text-sm font-medium bg-black text-white dark:bg-white dark:text-black rounded-full transition hover:opacity-90 flex items-center justify-center gap-2"
										on:click={() => checkForVersionUpdates()}
										type="button"
									>
										{#if updateAvailable === null}
											{$i18n.t('Check for updates')}
										{:else if updateAvailable}
											{$i18n.t('Update to v{{version}}', { version: version.latest })}
										{:else}
											已是最新版本
										{/if}
									</button>
								{/if}

								<button
									class="w-full text-center px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 bg-transparent hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full transition"
									on:click={() => showChangelog.set(true)}
									type="button"
								>
									{$i18n.t("See what's new")}
								</button>
							</div>
						</div>

						<div
							class="bg-gray-50 dark:bg-gray-850 rounded-lg p-4 flex flex-col justify-between border border-gray-100 dark:border-gray-800"
						>
							<div>
								<div class="text-xs font-medium text-gray-500 mb-2">{$i18n.t('About')}</div>
								<div class="flex flex-col gap-2.5">
									<a
										href="https://docs.openwebui.cn/"
										target="_blank"
										class="flex items-center gap-2.5 text-sm font-medium text-gray-700 dark:text-gray-200 hover:text-blue-600 dark:hover:text-blue-400 transition"
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 24 24"
											fill="currentColor"
											class="w-5 h-5 opacity-70"
										>
											<path
												d="M11.25 4.533A9.707 9.707 0 006 3a9.735 9.735 0 00-3.25.555.75.75 0 00-.5.707v14.25a.75.75 0 001 .75c.799 0 1.579-.17 2.25-.515.65.347 1.408.514 2.25.514 1.304 0 2.508-.346 3.498-1.002.046-.03.093-.061.14-.092A9.71 9.71 0 0118 19.5c.789 0 1.543-.162 2.25-.48a.75.75 0 00-.5-1.396A8.21 8.21 0 0018 18a8.215 8.215 0 00-3.528-1.07V4.532zM12.75 4.533c.961-.636 2.13-1.001 3.42-1.001A9.713 9.713 0 0121.75 4.25a.75.75 0 01-.5.707V19.2a.75.75 0 01-1 .75c-.799 0-1.579.17-2.25.515-.65-.347-1.408-.514-2.25-.514-1.304 0-2.508.346-3.498 1.002-.046.03-.093.061-.14.092A9.71 9.71 0 0111.25 19.5v-14.967z"
											/>
										</svg>
										<span>{$i18n.t('Documentation')}</span>
									</a>
									<a
										href="https://github.com/ztx888/open-webui"
										target="_blank"
										class="flex items-center gap-2.5 text-sm font-medium text-gray-700 dark:text-gray-200 hover:text-blue-600 dark:hover:text-blue-400 transition"
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 24 24"
											fill="currentColor"
											class="w-5 h-5 opacity-70"
										>
											<path
												fill-rule="evenodd"
												d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
												clip-rule="evenodd"
											/>
										</svg>
										<span>{$i18n.t('GitHub Repository')}</span>
									</a>
								</div>
							</div>

							<div class="mt-4 pt-4 border-t border-gray-100 dark:border-gray-800">
								<a href="https://github.com/ztx888/open-webui" target="_blank" class="block">
									<img
										alt="Github Repo"
										src="https://img.shields.io/github/stars/ztx888/open-webui?style=social&label=Star us on Github"
										class="h-5"
									/>
								</a>
							</div>
						</div>
					</div>
				</div>

				<!-- Identity & Security -->
				<div class="mb-4">
					<div class="flex flex-col gap-4">
						<div
							class="bg-gray-50 dark:bg-gray-850 rounded-lg p-5 border border-gray-100 dark:border-gray-800"
						>
							<div class="flex items-center gap-2.5 mb-5">
								<div class="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-900/30">
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-4 h-4 text-blue-600 dark:text-blue-400">
										<path fill-rule="evenodd" d="M12 1.5a5.25 5.25 0 00-5.25 5.25v3a3 3 0 00-3 3v6.75a3 3 0 003 3h10.5a3 3 0 003-3v-6.75a3 3 0 00-3-3v-3c0-2.9-2.35-5.25-5.25-5.25zm3.75 8.25v-3a3.75 3.75 0 10-7.5 0v3h7.5z" clip-rule="evenodd" />
									</svg>
								</div>
								<div class="text-base font-semibold text-gray-800 dark:text-gray-100">
									{$i18n.t('Identity & Security')}
								</div>
							</div>

							<div class="flex flex-col gap-5">
								<!-- 用户注册设置 -->
								<div class="space-y-3">
									<div class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
										{$i18n.t('User Registration')}
									</div>
									<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
										<div class="bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
											<div class="flex items-center justify-between">
												<div class="text-sm font-medium">{$i18n.t('Default User Role')}</div>
												<select
													class="dark:bg-gray-800 w-fit pr-8 rounded-lg px-2 py-1 text-sm bg-gray-50 outline-none focus:ring-0 border border-gray-200 dark:border-gray-700 text-right cursor-pointer"
													bind:value={adminConfig.DEFAULT_USER_ROLE}
													placeholder={$i18n.t('Select a role')}
												>
													<option value="pending">{$i18n.t('pending')}</option>
													<option value="user">{$i18n.t('user')}</option>
													<option value="admin">{$i18n.t('admin')}</option>
												</select>
											</div>
										</div>
										<div class="bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
											<div class="flex items-center justify-between">
												<div class="text-sm font-medium">{$i18n.t('Default Group')}</div>
												<select
													class="dark:bg-gray-800 w-fit pr-8 rounded-lg px-2 py-1 text-sm bg-gray-50 outline-none focus:ring-0 border border-gray-200 dark:border-gray-700 text-right cursor-pointer"
													bind:value={adminConfig.DEFAULT_GROUP_ID}
													placeholder={$i18n.t('Select a group')}
												>
													<option value={''}>None</option>
													{#each groups as group}
														<option value={group.id}>{group.name}</option>
													{/each}
												</select>
											</div>
										</div>
										<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
											<div class="text-sm font-medium">{$i18n.t('Enable New Sign Ups')}</div>
											<Switch bind:state={adminConfig.ENABLE_SIGNUP} />
										</div>
										<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
											<div class="text-sm font-medium">{$i18n.t('Show Admin Details in Account Pending Overlay')}</div>
											<Switch bind:state={adminConfig.SHOW_ADMIN_DETAILS} />
										</div>
									</div>

									{#if adminConfig.SHOW_ADMIN_DETAILS}
										<div class="bg-white dark:bg-gray-900 rounded-lg p-4 border border-gray-100 dark:border-gray-800">
											<div class="text-xs font-medium text-gray-500 mb-1.5">
												{$i18n.t('Admin Contact Email')}
											</div>
											<input
												class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:bg-gray-800 dark:text-gray-300 border border-gray-200 dark:border-gray-700 outline-none focus:border-gray-400 dark:focus:border-gray-600 transition"
												type="email"
												placeholder={$i18n.t('Leave empty to use first admin user')}
												bind:value={adminConfig.ADMIN_EMAIL}
											/>
										</div>
									{/if}

									<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
										<div class="bg-white dark:bg-gray-900 rounded-lg p-4 border border-gray-100 dark:border-gray-800">
											<div class="text-xs font-medium text-gray-500 mb-1.5">
												{$i18n.t('Pending User Overlay Title')}
											</div>
											<input
												class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:bg-gray-800 dark:text-gray-300 border border-gray-200 dark:border-gray-700 outline-none focus:border-gray-400 dark:focus:border-gray-600 transition"
												placeholder={$i18n.t(
													'Enter a title for the pending user info overlay. Leave empty for default.'
												)}
												bind:value={adminConfig.PENDING_USER_OVERLAY_TITLE}
											/>
										</div>
										<div class="bg-white dark:bg-gray-900 rounded-lg p-4 border border-gray-100 dark:border-gray-800">
											<div class="text-xs font-medium text-gray-500 mb-1.5">
												{$i18n.t('Pending User Overlay Content')}
											</div>
											<Textarea
												placeholder={$i18n.t(
													'Enter content for the pending user info overlay. Leave empty for default.'
												)}
												bind:value={adminConfig.PENDING_USER_OVERLAY_CONTENT}
											/>
										</div>
									</div>
								</div>

								<!-- API 密钥设置 -->
								<div class="space-y-3">
									<div class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
										{$i18n.t('API Keys')}
									</div>
									<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
										<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
											<div class="text-sm font-medium">{$i18n.t('Enable API Keys')}</div>
											<Switch bind:state={adminConfig.ENABLE_API_KEYS} />
										</div>
										{#if adminConfig?.ENABLE_API_KEYS}
											<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
												<div class="text-sm font-medium">{$i18n.t('API Key Endpoint Restrictions')}</div>
												<Switch bind:state={adminConfig.ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS} />
											</div>
										{/if}
									</div>

									{#if adminConfig?.ENABLE_API_KEYS && adminConfig?.ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS}
										<div class="ml-0 md:ml-4 bg-white dark:bg-gray-900 rounded-lg p-4 border border-gray-100 dark:border-gray-800">
											<div class="text-xs font-medium text-gray-500 mb-1.5">
												{$i18n.t('Allowed Endpoints')}
											</div>
											<input
												class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:bg-gray-800 dark:text-gray-300 border border-gray-200 dark:border-gray-700 outline-none focus:border-gray-400 dark:focus:border-gray-600 transition"
												type="text"
												placeholder={`e.g.) /api/v1/messages, /api/v1/channels`}
												bind:value={adminConfig.API_KEYS_ALLOWED_ENDPOINTS}
											/>
											<div class="mt-1.5 text-xs text-gray-400 dark:text-gray-500">
												<a
													href="https://docs.openwebui.cn/getting-started/api-endpoints"
													target="_blank"
													class="text-gray-500 dark:text-gray-400 font-medium underline hover:text-blue-500"
												>
													{$i18n.t(
														'To learn more about available endpoints, visit our documentation.'
													)}
												</a>
											</div>
										</div>
									{/if}
								</div>

								<!-- JWT 设置 -->
								<div class="space-y-3">
									<div class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
										{$i18n.t('Session Security')}
									</div>
									<div class="bg-white dark:bg-gray-900 rounded-lg p-4 border border-gray-100 dark:border-gray-800">
										<div class="text-xs font-medium text-gray-500 mb-1.5">{$i18n.t('JWT Expiration')}</div>
										<input
											class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:bg-gray-800 dark:text-gray-300 border border-gray-200 dark:border-gray-700 outline-none focus:border-gray-400 dark:focus:border-gray-600 transition"
											type="text"
											placeholder={`e.g.) "30m","1h", "10d". `}
											bind:value={adminConfig.JWT_EXPIRES_IN}
										/>
										<div class="mt-1.5 text-xs text-gray-400 dark:text-gray-500">
											{$i18n.t('Valid time units:')}
											<span class="text-gray-500 dark:text-gray-400 font-medium"
												>{$i18n.t("'s', 'm', 'h', 'd', 'w' or '-1' for no expiration.")}</span
											>
										</div>

										{#if adminConfig.JWT_EXPIRES_IN === '-1'}
											<div
												class="mt-3 bg-yellow-500/10 text-yellow-700 dark:text-yellow-200 rounded-lg px-4 py-3 text-xs flex items-center gap-2"
											>
												<span class="font-medium">{$i18n.t('Warning')}:</span>
												<span>
													<a
														href="https://docs.openwebui.cn/getting-started/env-configuration#jwt_expires_in"
														target="_blank"
														class="underline hover:text-yellow-800 dark:hover:text-yellow-100"
													>
														{$i18n.t('No expiration can pose security risks.')}
													</a>
												</span>
											</div>
										{/if}
									</div>
								</div>

								<!-- LDAP 设置 -->
								<div class="space-y-3">
									<div class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
										{$i18n.t('LDAP Authentication')}
									</div>
									<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
										<div class="text-sm font-medium">{$i18n.t('LDAP')}</div>
										<Switch bind:state={ENABLE_LDAP} />
									</div>

									{#if ENABLE_LDAP}
										<div class="pl-0 md:pl-2 space-y-4 pt-2">
											<div class="flex flex-col gap-1">
												<div class="text-xs font-medium text-gray-500 mb-1.5">
													{$i18n.t('Server Config')}
												</div>
												<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
													<div class="w-full">
														<input
															class="w-full rounded-lg py-2 px-3 text-sm bg-white dark:bg-gray-900 dark:text-gray-300 border border-gray-100 dark:border-gray-800 outline-none focus:border-gray-300 dark:focus:border-gray-700 transition"
															required
															placeholder={$i18n.t('Label (e.g. My LDAP)')}
															bind:value={LDAP_SERVER.label}
														/>
													</div>
													<div class="w-full">
														<input
															class="w-full rounded-lg py-2 px-3 text-sm bg-white dark:bg-gray-900 dark:text-gray-300 border border-gray-100 dark:border-gray-800 outline-none focus:border-gray-300 dark:focus:border-gray-700 transition"
															required
															placeholder={$i18n.t('Host (e.g. ldap.example.com)')}
															bind:value={LDAP_SERVER.host}
														/>
													</div>
													<div class="w-full">
														<Tooltip
															content={$i18n.t('Default to 389 or 636 if TLS is enabled')}
															placement="top-start"
															className="w-full"
														>
															<input
																class="w-full rounded-lg py-2 px-3 text-sm bg-white dark:bg-gray-900 dark:text-gray-300 border border-gray-100 dark:border-gray-800 outline-none focus:border-gray-300 dark:focus:border-gray-700 transition"
																type="number"
																placeholder={$i18n.t('Port')}
																bind:value={LDAP_SERVER.port}
															/>
														</Tooltip>
													</div>
												</div>
											</div>

											<div class="flex flex-col gap-1">
												<div class="text-xs font-medium text-gray-500 mb-1.5">
													{$i18n.t('Authentication')}
												</div>
												<div class="grid grid-cols-1 gap-3">
													<div class="w-full">
														<Tooltip
															content={$i18n.t(
																'The Application Account DN you bind with for search'
															)}
															placement="top-start"
														>
															<input
																class="w-full rounded-lg py-2 px-3 text-sm bg-white dark:bg-gray-900 dark:text-gray-300 border border-gray-100 dark:border-gray-800 outline-none focus:border-gray-300 dark:focus:border-gray-700 transition"
																required
																placeholder={$i18n.t('Application DN')}
																bind:value={LDAP_SERVER.app_dn}
															/>
														</Tooltip>
													</div>
													<div class="w-full">
														<SensitiveInput
															placeholder={$i18n.t('Application DN Password')}
															bind:value={LDAP_SERVER.app_dn_password}
														/>
													</div>
												</div>
											</div>

											<div class="flex flex-col gap-1">
												<div class="text-xs font-medium text-gray-500 mb-1.5">
													{$i18n.t('User Mapping')}
												</div>
												<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
													<div class="w-full">
														<Tooltip
															content={$i18n.t(
																'The LDAP attribute that maps to the mail that users use to sign in.'
															)}
															placement="top-start"
														>
															<input
																class="w-full rounded-lg py-2 px-3 text-sm bg-white dark:bg-gray-900 dark:text-gray-300 border border-gray-100 dark:border-gray-800 outline-none focus:border-gray-300 dark:focus:border-gray-700 transition"
																required
																placeholder={$i18n.t('Mail Attribute (e.g. mail)')}
																bind:value={LDAP_SERVER.attribute_for_mail}
															/>
														</Tooltip>
													</div>
													<div class="w-full">
														<Tooltip
															content={$i18n.t(
																'The LDAP attribute that maps to the username that users use to sign in.'
															)}
															placement="top-start"
														>
															<input
																class="w-full rounded-lg py-2 px-3 text-sm bg-white dark:bg-gray-900 dark:text-gray-300 border border-gray-100 dark:border-gray-800 outline-none focus:border-gray-300 dark:focus:border-gray-700 transition"
																required
																placeholder={$i18n.t('Username Attribute (e.g. uid)')}
																bind:value={LDAP_SERVER.attribute_for_username}
															/>
														</Tooltip>
													</div>
												</div>
											</div>

											<div class="flex flex-col gap-1">
												<div class="text-xs font-medium text-gray-500 mb-1.5">
													{$i18n.t('Search')}
												</div>
												<div class="space-y-3">
													<div class="w-full">
														<Tooltip
															content={$i18n.t('The base to search for users')}
															placement="top-start"
														>
															<input
																class="w-full rounded-lg py-2 px-3 text-sm bg-white dark:bg-gray-900 dark:text-gray-300 border border-gray-100 dark:border-gray-800 outline-none focus:border-gray-300 dark:focus:border-gray-700 transition"
																required
																placeholder={$i18n.t(
																	'Search Base (e.g. ou=users,dc=example,dc=com)'
																)}
																bind:value={LDAP_SERVER.search_base}
															/>
														</Tooltip>
													</div>
													<div class="w-full">
														<input
															class="w-full rounded-lg py-2 px-3 text-sm bg-white dark:bg-gray-900 dark:text-gray-300 border border-gray-100 dark:border-gray-800 outline-none focus:border-gray-300 dark:focus:border-gray-700 transition"
															placeholder={$i18n.t(
																'Search Filters (e.g. (&(objectClass=inetOrgPerson)(uid=%s)))'
															)}
															bind:value={LDAP_SERVER.search_filters}
														/>
													</div>
													<div class="text-xs text-gray-400 dark:text-gray-500 text-right">
														<a
															class="hover:text-gray-700 dark:hover:text-gray-300 transition underline"
															href="https://ldap.com/ldap-filters/"
															target="_blank"
														>
															{$i18n.t('Click here for filter guides.')}
														</a>
													</div>
												</div>
											</div>

											<!-- TLS Settings -->
											<div class="pt-2">
												<div class="flex justify-between items-center mb-3">
													<div class="text-sm font-medium">{$i18n.t('TLS Encryption')}</div>
													<Switch bind:state={LDAP_SERVER.use_tls} />
												</div>

												{#if LDAP_SERVER.use_tls}
													<div class="pl-2 space-y-3">
														<div class="flex justify-between items-center">
															<div class="text-xs font-medium">
																{$i18n.t('Validate certificate')}
															</div>
															<Switch bind:state={LDAP_SERVER.validate_cert} />
														</div>

														<div class="w-full">
															<div class="text-xs font-medium text-gray-500 mb-1.5">
																{$i18n.t('Certificate Path')}
															</div>
															<input
																class="w-full rounded-lg py-2 px-3 text-sm bg-white dark:bg-gray-900 dark:text-gray-300 border border-gray-100 dark:border-gray-800 outline-none focus:border-gray-300 dark:focus:border-gray-700 transition"
																placeholder={$i18n.t('Enter certificate path')}
																bind:value={LDAP_SERVER.certificate_path}
															/>
														</div>

														<div class="w-full">
															<div class="text-xs font-medium text-gray-500 mb-1.5">
																{$i18n.t('Ciphers')}
															</div>
															<Tooltip content={$i18n.t('Default to ALL')} placement="top-start">
																<input
																	class="w-full rounded-lg py-2 px-3 text-sm bg-white dark:bg-gray-900 dark:text-gray-300 border border-gray-100 dark:border-gray-800 outline-none focus:border-gray-300 dark:focus:border-gray-700 transition"
																	placeholder={$i18n.t('Example: ALL')}
																	bind:value={LDAP_SERVER.ciphers}
																/>
															</Tooltip>
														</div>
													</div>
												{/if}
											</div>
										</div>
									{/if}
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- Application Features -->
				<div class="mb-4">
					<div
						class="bg-gray-50 dark:bg-gray-850 rounded-lg p-5 border border-gray-100 dark:border-gray-800"
					>
						<div class="flex items-center gap-2.5 mb-5">
							<div class="flex items-center justify-center w-8 h-8 rounded-lg bg-purple-100 dark:bg-purple-900/30">
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-4 h-4 text-purple-600 dark:text-purple-400">
									<path fill-rule="evenodd" d="M9 4.5a.75.75 0 01.721.544l.813 2.846a3.75 3.75 0 002.576 2.576l2.846.813a.75.75 0 010 1.442l-2.846.813a3.75 3.75 0 00-2.576 2.576l-.813 2.846a.75.75 0 01-1.442 0l-.813-2.846a3.75 3.75 0 00-2.576-2.576l-2.846-.813a.75.75 0 010-1.442l2.846-.813A3.75 3.75 0 007.466 7.89l.813-2.846A.75.75 0 019 4.5zM18 1.5a.75.75 0 01.728.568l.258 1.036c.236.94.97 1.674 1.91 1.91l1.036.258a.75.75 0 010 1.456l-1.036.258c-.94.236-1.674.97-1.91 1.91l-.258 1.036a.75.75 0 01-1.456 0l-.258-1.036a2.625 2.625 0 00-1.91-1.91l-1.036-.258a.75.75 0 010-1.456l1.036-.258a2.625 2.625 0 001.91-1.91l.258-1.036A.75.75 0 0118 1.5zM16.5 15a.75.75 0 01.712.513l.394 1.183c.15.447.5.799.948.948l1.183.395a.75.75 0 010 1.422l-1.183.395c-.447.15-.799.5-.948.948l-.395 1.183a.75.75 0 01-1.422 0l-.395-1.183a1.5 1.5 0 00-.948-.948l-1.183-.395a.75.75 0 010-1.422l1.183-.395c.447-.15.799-.5.948-.948l.395-1.183A.75.75 0 0116.5 15z" clip-rule="evenodd" />
								</svg>
							</div>
							<div class="text-base font-semibold text-gray-800 dark:text-gray-100">
								{$i18n.t('App Features')}
							</div>
						</div>

						<div class="flex flex-col gap-5">
							<!-- 社区与互动 -->
							<div class="space-y-3">
								<div class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
									{$i18n.t('Community & Interaction')}
								</div>
								<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
									<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
										<div class="text-sm font-medium">{$i18n.t('Enable Community Sharing')}</div>
										<Switch bind:state={adminConfig.ENABLE_COMMUNITY_SHARING} />
									</div>
									<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
										<div class="text-sm font-medium">{$i18n.t('Enable Message Rating')}</div>
										<Switch bind:state={adminConfig.ENABLE_MESSAGE_RATING} />
									</div>
								</div>
							</div>

							<!-- 内容管理 -->
							<div class="space-y-3">
								<div class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
									{$i18n.t('Content Management')}
								</div>
								<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
									<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
										<div class="text-sm font-medium">{$i18n.t('Enable Folders')}</div>
										<Switch bind:state={adminConfig.ENABLE_FOLDERS} />
									</div>
									<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
										<div class="text-sm font-medium">
											{$i18n.t('Enable Notes')}
											<span class="ml-1 text-xs px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded">{$i18n.t('Beta')}</span>
										</div>
										<Switch bind:state={adminConfig.ENABLE_NOTES} />
									</div>
									<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
										<div class="text-sm font-medium">
											{$i18n.t('Enable Channels')}
											<span class="ml-1 text-xs px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded">{$i18n.t('Beta')}</span>
										</div>
										<Switch bind:state={adminConfig.ENABLE_CHANNELS} />
									</div>
									<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
										<div class="text-sm font-medium">
											{$i18n.t('Enable Memories')}
											<span class="ml-1 text-xs px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded">{$i18n.t('Beta')}</span>
										</div>
										<Switch bind:state={adminConfig.ENABLE_MEMORIES} />
									</div>
								</div>

								{#if adminConfig.ENABLE_FOLDERS}
									<div class="bg-white dark:bg-gray-900 rounded-lg p-4 border border-gray-100 dark:border-gray-800">
										<div class="text-xs font-medium text-gray-500 mb-1.5">
											{$i18n.t('Folder Max File Count')}
										</div>
										<input
											class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:bg-gray-800 dark:text-gray-300 border border-gray-200 dark:border-gray-700 outline-none focus:border-gray-400 dark:focus:border-gray-600 transition"
											type="number"
											min="0"
											placeholder={$i18n.t('Leave empty for unlimited')}
											bind:value={adminConfig.FOLDER_MAX_FILE_COUNT}
										/>
										<div class="mt-1.5 text-xs text-gray-400 dark:text-gray-500">
											{$i18n.t('Maximum number of files allowed per folder.')}
										</div>
									</div>
								{/if}
							</div>

							<!-- 用户功能 -->
							<div class="space-y-3">
								<div class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
									{$i18n.t('User Features')}
								</div>
								<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
									<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
										<div class="text-sm font-medium">{$i18n.t('Enable User Webhooks')}</div>
										<Switch bind:state={adminConfig.ENABLE_USER_WEBHOOKS} />
									</div>
									<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
										<div class="text-sm font-medium">{$i18n.t('Enable User Status')}</div>
										<Switch bind:state={adminConfig.ENABLE_USER_STATUS} />
									</div>
								</div>
							</div>

							<!-- 其他设置 -->
							<div class="space-y-3">
								<div class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
									{$i18n.t('Other Settings')}
								</div>
								<div class="bg-white dark:bg-gray-900 rounded-lg p-4 border border-gray-100 dark:border-gray-800">
									<div class="text-xs font-medium text-gray-500 mb-1.5">
										{$i18n.t('Response Watermark')}
									</div>
									<input
										class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:bg-gray-800 dark:text-gray-300 border border-gray-200 dark:border-gray-700 outline-none focus:border-gray-400 dark:focus:border-gray-600 transition"
										placeholder={$i18n.t('Enter a watermark for the response. Leave empty for none.')}
										bind:value={adminConfig.RESPONSE_WATERMARK}
									/>
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- System Settings -->
				<div class="mb-4">
					<div
						class="bg-gray-50 dark:bg-gray-850 rounded-lg p-5 border border-gray-100 dark:border-gray-800"
					>
						<div class="flex items-center gap-2.5 mb-5">
							<div class="flex items-center justify-center w-8 h-8 rounded-lg bg-green-100 dark:bg-green-900/30">
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-4 h-4 text-green-600 dark:text-green-400">
									<path fill-rule="evenodd" d="M2.25 6a3 3 0 013-3h13.5a3 3 0 013 3v12a3 3 0 01-3 3H5.25a3 3 0 01-3-3V6zm3.97.97a.75.75 0 011.06 0l2.25 2.25a.75.75 0 010 1.06l-2.25 2.25a.75.75 0 01-1.06-1.06l1.72-1.72-1.72-1.72a.75.75 0 010-1.06zm4.28 4.28a.75.75 0 000 1.5h3a.75.75 0 000-1.5h-3z" clip-rule="evenodd" />
								</svg>
							</div>
							<div class="text-base font-semibold text-gray-800 dark:text-gray-100">
								{$i18n.t('System Connections')}
							</div>
						</div>

						<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
							<div
								class="bg-white dark:bg-gray-900 rounded-lg p-4 border border-gray-100 dark:border-gray-800"
							>
								<div class="flex items-center gap-2 mb-3">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 24 24"
										fill="currentColor"
										class="w-5 h-5 opacity-70 text-gray-600 dark:text-gray-400"
									>
										<path
											fill-rule="evenodd"
											d="M19.902 4.098a3.75 3.75 0 00-5.304 0l-4.5 4.5a3.75 3.75 0 001.035 6.037.75.75 0 01-.646 1.353 5.25 5.25 0 01-1.449-8.45l4.5-4.5a5.25 5.25 0 117.424 7.424l-1.757 1.757a.75.75 0 11-1.06-1.06l1.757-1.757a3.75 3.75 0 000-5.304zm-7.389 4.267a.75.75 0 011-.353 5.25 5.25 0 011.449 8.45l-4.5 4.5a5.25 5.25 0 11-7.424-7.424l1.757-1.757a.75.75 0 111.06 1.06l-1.757 1.757a3.75 3.75 0 105.304 5.304l4.5-4.5a3.75 3.75 0 00-1.035-6.037.75.75 0 01-.354-1z"
											clip-rule="evenodd"
										/>
									</svg>
									<div class="text-xs font-medium text-gray-500">{$i18n.t('WebUI URL')}</div>
								</div>
								<div>
									<input
										class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:bg-gray-800 dark:text-gray-300 border border-gray-200 dark:border-gray-700 outline-none focus:border-gray-400 dark:focus:border-gray-600 transition"
										type="text"
										placeholder={`e.g.) "http://localhost:3000"`}
										bind:value={adminConfig.WEBUI_URL}
									/>
									<div class="mt-2 text-xs text-gray-500 dark:text-gray-400">
										{$i18n.t(
											'Enter the public URL of your WebUI. This URL will be used to generate links in the notifications.'
										)}
									</div>
								</div>
							</div>

							<div
								class="bg-white dark:bg-gray-900 rounded-lg p-4 border border-gray-100 dark:border-gray-800"
							>
								<div class="flex items-center gap-2 mb-3">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 24 24"
										fill="currentColor"
										class="w-5 h-5 opacity-70 text-gray-600 dark:text-gray-400"
									>
										<path
											fill-rule="evenodd"
											d="M5.337 21.718a6.707 6.707 0 01-.533-.074.75.75 0 01-.44-1.223 3.73 3.73 0 00.814-1.686c.023-.115-.022-.317-.254-.543C3.274 16.587 2.25 14.41 2.25 12c0-5.03 4.428-9 9.75-9s9.75 3.97 9.75 9c0 5.03-4.428 9-9.75 9-.833 0-1.643-.097-2.417-.279a6.721 6.721 0 01-4.246.997z"
											clip-rule="evenodd"
										/>
									</svg>
									<div class="text-xs font-medium text-gray-500">{$i18n.t('Webhook URL')}</div>
								</div>
								<div>
									<input
										class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:bg-gray-800 dark:text-gray-300 border border-gray-200 dark:border-gray-700 outline-none focus:border-gray-400 dark:focus:border-gray-600 transition"
										type="text"
										placeholder={`https://example.com/webhook`}
										bind:value={webhookUrl}
									/>
									<div class="mt-2 text-xs text-gray-500 dark:text-gray-400">
										{$i18n.t('Configure webhook endpoint for system notifications')}
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
