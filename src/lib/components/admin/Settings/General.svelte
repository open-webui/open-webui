<script lang="ts">
	import DOMPurify from 'dompurify';

	import { getBackendConfig, getVersionUpdates, getWebhookUrl, updateWebhookUrl } from '$lib/apis';
	import {
		getAdminConfig,
		getLdapConfig,
		getLdapServer,
		updateAdminConfig,
		updateLdapConfig,
		updateLdapServer
	} from '$lib/apis/auths';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { WEBUI_BUILD_HASH, WEBUI_VERSION } from '$lib/constants';
	import { config, showChangelog } from '$lib/stores';
	import { compareVersion } from '$lib/utils';
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let updateAvailable = null;
	let version = {
		current: '',
		latest: ''
	};

	let adminConfig = null;
	let webhookUrl = '';

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
		version = await getVersionUpdates(localStorage.token).catch((error) => {
			return {
				current: WEBUI_VERSION,
				latest: WEBUI_VERSION
			};
		});

		console.log(version);

		updateAvailable = compareVersion(version.latest, version.current);
		console.log(updateAvailable);
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
		const res = await updateAdminConfig(localStorage.token, adminConfig);
		await updateLdapServerHandler();

		if (res) {
			saveHandler();
		} else {
			toast.error(i18n.t('Failed to update settings'));
		}
	};

	onMount(async () => {
		checkForVersionUpdates();

		await Promise.all([
			(async () => {
				adminConfig = await getAdminConfig(localStorage.token);
			})(),

			(async () => {
				webhookUrl = await getWebhookUrl(localStorage.token);
			})(),
			(async () => {
				LDAP_SERVER = await getLdapServer(localStorage.token);
			})()
		]);

		const ldapConfig = await getLdapConfig(localStorage.token);
		ENABLE_LDAP = ldapConfig.ENABLE_LDAP;
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={async () => {
		updateHandler();
	}}
>
	<div class="mt-0.5 space-y-3 overflow-y-scroll scrollbar-hidden h-full" style="padding-right: 4px;">
		{#if adminConfig !== null}
			<div class="">
				<!-- General Section -->
				<div class="mb-6 bg-gradient-to-b from-gray-50/50 to-transparent dark:from-gray-800/20 dark:to-transparent rounded-xl p-5 border border-gray-200/60 dark:border-gray-700/30">
					<div class="mb-4 flex items-center gap-2">
						<div class="w-1 h-6 bg-orange-500 rounded-sm"></div>
						<div class="text-base font-semibold text-gray-900 dark:text-gray-100" style="letter-spacing: -0.01em;">{$i18n.t('General')}</div>
					</div>

					<!-- Version Info Card -->
					<div class="mb-4 bg-white dark:bg-gray-800/50 rounded-lg p-4 shadow-sm border border-gray-200/80 dark:border-gray-700/50">
						<div class="mb-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
							{$i18n.t('Version')}
						</div>
						<div class="flex w-full justify-between items-center">
							<div class="flex flex-col text-xs text-gray-700 dark:text-gray-300 gap-1.5">
								<div class="flex gap-1 items-center">
									<Tooltip content={WEBUI_BUILD_HASH}>
										<span class="font-mono bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded text-xs font-semibold text-gray-800 dark:text-gray-200">v{WEBUI_VERSION}</span>
									</Tooltip>

									<a
										href="https://github.com/open-webui/open-webui/releases/tag/v{version.latest}"
										target="_blank"
										class="text-blue-600 dark:text-blue-400 font-medium hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
									>
										{updateAvailable === null
											? $i18n.t('Checking for updates...')
											: updateAvailable
												? `(v${version.latest} ${$i18n.t('available!')})`
												: $i18n.t('(latest)')}
									</a>
								</div>

								<button
									class="underline flex items-center space-x-1 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition-colors w-fit"
									type="button"
									on:click={() => {
										showChangelog.set(true);
									}}
								>
									<div>{$i18n.t("See what's new")}</div>
								</button>
							</div>

							<button
								class="text-xs px-3 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 transition-colors rounded-lg font-semibold shadow-sm border border-gray-300/50 dark:border-gray-600/50"
								type="button"
								on:click={() => {
									checkForVersionUpdates();
								}}
							>
								{$i18n.t('Check for updates')}
							</button>
						</div>
					</div>

					<!-- Help Card -->
					<div class="mb-4 bg-white dark:bg-gray-800/50 rounded-lg p-4 shadow-sm border border-gray-200/80 dark:border-gray-700/50">
						<div class="flex w-full justify-between items-center">
							<div class="text-xs pr-2">
								<div class="font-semibold text-gray-900 dark:text-gray-100 mb-1 text-sm">
									{$i18n.t('Help')}
								</div>
								<div class="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
									{$i18n.t('Discover how to use Open WebUI and seek support from the community.')}
								</div>
							</div>

							<a
								class="flex-shrink-0 text-xs font-semibold underline text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 whitespace-nowrap transition-colors"
								href="https://docs.openwebui.com/"
								target="_blank"
							>
								{$i18n.t('Documentation')}
							</a>
						</div>

						<div class="mt-3 pt-3 border-t border-gray-200/80 dark:border-gray-700/50">
							<div class="flex flex-wrap gap-1.5">
								<a href="https://discord.gg/5rJgQTnV4s" target="_blank" class="transition-transform hover:scale-105">
									<img
										alt="Discord"
										src="https://img.shields.io/badge/Discord-Open_WebUI-blue?logo=discord&logoColor=white"
										class="rounded"
									/>
								</a>

								<a href="https://twitter.com/OpenWebUI" target="_blank" class="transition-transform hover:scale-105">
									<img
										alt="X (formerly Twitter) Follow"
										src="https://img.shields.io/twitter/follow/OpenWebUI"
										class="rounded"
									/>
								</a>

								<a href="https://github.com/open-webui/open-webui" target="_blank" class="transition-transform hover:scale-105">
									<img
										alt="Github Repo"
										src="https://img.shields.io/github/stars/open-webui/open-webui?style=social&label=Star us on Github"
										class="rounded"
									/>
								</a>
							</div>
						</div>
					</div>

					<!-- License Card -->
					<div class="mb-2 bg-white dark:bg-gray-800/50 rounded-lg p-4 shadow-sm border border-gray-200/80 dark:border-gray-700/50">
						<div class="flex w-full justify-between items-center">
							<div class="text-xs pr-2">
								<div class="font-semibold text-gray-900 dark:text-gray-100 mb-1 text-sm">
									{$i18n.t('License')}
								</div>

								{#if $config?.license_metadata}
									<a
										href="https://docs.openwebui.com/enterprise"
										target="_blank"
										class="text-gray-600 dark:text-gray-400 mt-1 leading-relaxed"
									>
										<span class="capitalize text-gray-900 dark:text-gray-100 font-medium"
											>{$config?.license_metadata?.type}
											license</span
										>
										registered to
										<span class="capitalize text-gray-900 dark:text-gray-100 font-medium"
											>{$config?.license_metadata?.organization_name}</span
										>
										for
										<span class="font-semibold text-gray-900 dark:text-gray-100"
											>{$config?.license_metadata?.seats ?? 'Unlimited'} users.</span
										>
									</a>
									{#if $config?.license_metadata?.html}
										<div class="mt-1">
											{@html DOMPurify.sanitize($config?.license_metadata?.html)}
										</div>
									{/if}
								{:else}
									<a
										class="text-xs hover:underline text-gray-600 dark:text-gray-400 leading-relaxed transition-colors"
										href="https://docs.openwebui.com/enterprise"
										target="_blank"
									>
										<span>
											{$i18n.t(
												'Upgrade to a licensed plan for enhanced capabilities, including custom theming and branding, and dedicated support.'
											)}
										</span>
									</a>
								{/if}
							</div>
						</div>
					</div>
				</div>

				<!-- Authentication Section -->
				<div class="mb-6 bg-gradient-to-b from-gray-50/50 to-transparent dark:from-gray-800/20 dark:to-transparent rounded-xl p-5 border border-gray-200/60 dark:border-gray-700/30">
					<div class="mb-4 flex items-center gap-2">
						<div class="w-1 h-6 bg-orange-500 rounded-sm"></div>
						<div class="text-base font-semibold text-gray-900 dark:text-gray-100" style="letter-spacing: -0.01em;">{$i18n.t('Authentication')}</div>
					</div>

					<div class="space-y-3 bg-white dark:bg-gray-800/50 rounded-lg p-4 shadow-sm border border-gray-200/80 dark:border-gray-700/50">
						<!-- Default User Role -->
						<div class="flex w-full justify-between items-center py-2 border-b border-gray-200/60 dark:border-gray-700/40">
							<div class="self-center text-sm font-medium text-gray-800 dark:text-gray-200">{$i18n.t('Default User Role')}</div>
							<div class="flex items-center relative">
								<select
									class="w-fit pr-8 rounded-md px-3 py-1.5 text-xs bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 border border-gray-300/50 dark:border-gray-600/50 outline-none font-medium cursor-pointer transition-colors hover:bg-gray-200 dark:hover:bg-gray-600"
									bind:value={adminConfig.DEFAULT_USER_ROLE}
									placeholder="Select a role"
								>
									<option value="pending">{$i18n.t('pending')}</option>
									<option value="user">{$i18n.t('user')}</option>
									<option value="admin">{$i18n.t('admin')}</option>
								</select>
							</div>
						</div>

						<!-- Enable New Sign Ups -->
						<div class="flex w-full justify-between items-center py-2 border-b border-gray-200/60 dark:border-gray-700/40">
							<div class="self-center text-sm font-medium text-gray-800 dark:text-gray-200">{$i18n.t('Enable New Sign Ups')}</div>
							<Switch bind:state={adminConfig.ENABLE_SIGNUP} />
						</div>

						<!-- Show Admin Details -->
						<div class="flex w-full items-center justify-between py-2 border-b border-gray-200/60 dark:border-gray-700/40">
							<div class="self-center text-sm font-medium text-gray-800 dark:text-gray-200">
								{$i18n.t('Show Admin Details in Account Pending Overlay')}
							</div>
							<Switch bind:state={adminConfig.SHOW_ADMIN_DETAILS} />
						</div>

						<!-- Enable API Key -->
						<div class="flex w-full justify-between items-center py-2 border-b border-gray-200/60 dark:border-gray-700/40">
							<div class="self-center text-sm font-medium text-gray-800 dark:text-gray-200">{$i18n.t('Enable API Key')}</div>
							<Switch bind:state={adminConfig.ENABLE_API_KEY} />
						</div>

						{#if adminConfig?.ENABLE_API_KEY}
							<div class="flex w-full justify-between items-center py-2 pl-4 border-b border-gray-200/60 dark:border-gray-700/40 border-l-4 border-l-blue-500 dark:border-l-blue-400">
								<div class="self-center text-sm font-medium text-gray-800 dark:text-gray-200">
									{$i18n.t('API Key Endpoint Restrictions')}
								</div>
								<Switch bind:state={adminConfig.ENABLE_API_KEY_ENDPOINT_RESTRICTIONS} />
							</div>

							{#if adminConfig?.ENABLE_API_KEY_ENDPOINT_RESTRICTIONS}
								<div class="flex w-full flex-col py-3 pl-4 border-l-4 border-l-blue-500 dark:border-l-blue-400">
									<div class="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-2">
										{$i18n.t('Allowed Endpoints')}
									</div>

									<input
										class="w-full rounded-lg text-sm text-gray-800 dark:text-gray-200 bg-gray-100 dark:bg-gray-700 border border-gray-300/50 dark:border-gray-600/50 outline-none px-3.5 py-2.5 transition-colors focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20"
										type="text"
										placeholder={`e.g.) /api/v1/messages, /api/v1/channels`}
										bind:value={adminConfig.API_KEY_ALLOWED_ENDPOINTS}
									/>

									<div class="mt-2 text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
										<a
											href="https://docs.openwebui.com/getting-started/api-endpoints"
											target="_blank"
											class="text-blue-600 dark:text-blue-400 font-medium underline hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
										>
											{$i18n.t('To learn more about available endpoints, visit our documentation.')}
										</a>
									</div>
								</div>
							{/if}
						{/if}

						<!-- JWT Expiration -->
						<div class="w-full justify-between py-3 border-b border-gray-200/60 dark:border-gray-700/40">
							<div class="flex w-full justify-between mb-2">
								<div class="self-center text-sm font-semibold text-gray-800 dark:text-gray-200">{$i18n.t('JWT Expiration')}</div>
							</div>

							<div class="flex space-x-2">
								<input
									class="w-full rounded-lg py-2.5 px-3.5 text-sm bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 border border-gray-300/50 dark:border-gray-600/50 outline-none transition-colors focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20"
									type="text"
									placeholder={`e.g.) "30m","1h", "10d". `}
									bind:value={adminConfig.JWT_EXPIRES_IN}
								/>
							</div>

							<div class="mt-2 text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
								{$i18n.t('Valid time units:')}
								<span class="text-gray-800 dark:text-gray-200 font-semibold"
									>{$i18n.t("'s', 'm', 'h', 'd', 'w' or '-1' for no expiration.")}</span
								>
							</div>
						</div>

						<!-- LDAP Section -->
						<div class="space-y-3 pt-2">
							<div class="space-y-2">
								<div class="flex justify-between items-center text-sm py-2">
									<div class="font-semibold text-gray-800 dark:text-gray-200">{$i18n.t('LDAP')}</div>
									<div class="mt-1">
										<Switch
											bind:state={ENABLE_LDAP}
											on:change={async () => {
												updateLdapConfig(localStorage.token, ENABLE_LDAP);
											}}
										/>
									</div>
								</div>

								{#if ENABLE_LDAP}
									<div class="flex flex-col gap-3 bg-gray-100 dark:bg-gray-900/50 rounded-lg p-4 border border-gray-300/50 dark:border-gray-700/50">
										<div class="flex w-full gap-2">
											<div class="w-full">
												<div class="self-center text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider mb-1.5">
													{$i18n.t('Label')}
												</div>
												<input
													class="w-full bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-300/50 dark:border-gray-700/50 rounded-md px-3 py-2 outline-none transition-colors focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20"
													required
													placeholder={$i18n.t('Enter server label')}
													bind:value={LDAP_SERVER.label}
												/>
											</div>
											<div class="w-full"></div>
										</div>
										<div class="flex w-full gap-2">
											<div class="w-full">
												<div class="self-center text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider mb-1.5">
													{$i18n.t('Host')}
												</div>
												<input
													class="w-full bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-300/50 dark:border-gray-700/50 rounded-md px-3 py-2 outline-none transition-colors focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20"
													required
													placeholder={$i18n.t('Enter server host')}
													bind:value={LDAP_SERVER.host}
												/>
											</div>
											<div class="w-full">
												<div class="self-center text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider mb-1.5">
													{$i18n.t('Port')}
												</div>
												<Tooltip
													placement="top-start"
													content={$i18n.t('Default to 389 or 636 if TLS is enabled')}
													className="w-full"
												>
													<input
														class="w-full bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-300/50 dark:border-gray-700/50 rounded-md px-3 py-2 outline-none transition-colors focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20"
														type="number"
														placeholder={$i18n.t('Enter server port')}
														bind:value={LDAP_SERVER.port}
													/>
												</Tooltip>
											</div>
										</div>
										<div class="flex w-full gap-2">
											<div class="w-full">
												<div class="self-center text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider mb-1.5">
													{$i18n.t('Application DN')}
												</div>
												<Tooltip
													content={$i18n.t('The Application Account DN you bind with for search')}
													placement="top-start"
												>
													<input
														class="w-full bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-300/50 dark:border-gray-700/50 rounded-md px-3 py-2 outline-none transition-colors focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20"
														required
														placeholder={$i18n.t('Enter Application DN')}
														bind:value={LDAP_SERVER.app_dn}
													/>
												</Tooltip>
											</div>
											<div class="w-full">
												<div class="self-center text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider mb-1.5">
													{$i18n.t('Application DN Password')}
												</div>
												<SensitiveInput
													placeholder={$i18n.t('Enter Application DN Password')}
													bind:value={LDAP_SERVER.app_dn_password}
												/>
											</div>
										</div>
										<div class="flex w-full gap-2">
											<div class="w-full">
												<div class="self-center text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider mb-1.5">
													{$i18n.t('Attribute for Mail')}
												</div>
												<Tooltip
													content={$i18n.t(
														'The LDAP attribute that maps to the mail that users use to sign in.'
													)}
													placement="top-start"
												>
													<input
														class="w-full bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-300/50 dark:border-gray-700/50 rounded-md px-3 py-2 outline-none transition-colors focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20"
														required
														placeholder={$i18n.t('Example: mail')}
														bind:value={LDAP_SERVER.attribute_for_mail}
													/>
												</Tooltip>
											</div>
										</div>
										<div class="flex w-full gap-2">
											<div class="w-full">
												<div class="self-center text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider mb-1.5">
													{$i18n.t('Attribute for Username')}
												</div>
												<Tooltip
													content={$i18n.t(
														'The LDAP attribute that maps to the username that users use to sign in.'
													)}
													placement="top-start"
												>
													<input
														class="w-full bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-300/50 dark:border-gray-700/50 rounded-md px-3 py-2 outline-none transition-colors focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20"
														required
														placeholder={$i18n.t(
															'Example: sAMAccountName or uid or userPrincipalName'
														)}
														bind:value={LDAP_SERVER.attribute_for_username}
													/>
												</Tooltip>
											</div>
										</div>
										<div class="flex w-full gap-2">
											<div class="w-full">
												<div class="self-center text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider mb-1.5">
													{$i18n.t('Search Base')}
												</div>
												<Tooltip
													content={$i18n.t('The base to search for users')}
													placement="top-start"
												>
													<input
														class="w-full bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-300/50 dark:border-gray-700/50 rounded-md px-3 py-2 outline-none transition-colors focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20"
														required
														placeholder={$i18n.t('Example: ou=users,dc=foo,dc=example')}
														bind:value={LDAP_SERVER.search_base}
													/>
												</Tooltip>
											</div>
										</div>
										<div class="flex w-full gap-2">
											<div class="w-full">
												<div class="self-center text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider mb-1.5">
													{$i18n.t('Search Filters')}
												</div>
												<input
													class="w-full bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-300/50 dark:border-gray-700/50 rounded-md px-3 py-2 outline-none transition-colors focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20"
													placeholder={$i18n.t('Example: (&(objectClass=inetOrgPerson)(uid=%s))')}
													bind:value={LDAP_SERVER.search_filters}
												/>
											</div>
										</div>
										<div class="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
											<a
												class="text-blue-600 dark:text-blue-400 font-medium underline hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
												href="https://ldap.com/ldap-filters/"
												target="_blank"
											>
												{$i18n.t('Click here for filter guides.')}
											</a>
										</div>
										<div class="pt-3 border-t border-gray-300/50 dark:border-gray-700/50">
											<div class="flex justify-between items-center text-sm">
												<div class="font-semibold text-gray-800 dark:text-gray-200">{$i18n.t('TLS')}</div>
												<div class="mt-1">
													<Switch bind:state={LDAP_SERVER.use_tls} />
												</div>
											</div>
											{#if LDAP_SERVER.use_tls}
												<div class="flex w-full gap-2 mt-3">
													<div class="w-full">
														<div class="self-center text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider mb-1.5">
															{$i18n.t('Certificate Path')}
														</div>
														<input
															class="w-full bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-300/50 dark:border-gray-700/50 rounded-md px-3 py-2 outline-none transition-colors focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20"
															placeholder={$i18n.t('Enter certificate path')}
															bind:value={LDAP_SERVER.certificate_path}
														/>
													</div>
												</div>
												<div class="flex w-full gap-2 mt-3">
													<div class="w-full">
														<div class="self-center text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider mb-1.5">
															{$i18n.t('Ciphers')}
														</div>
														<Tooltip content={$i18n.t('Default to ALL')} placement="top-start">
															<input
																class="w-full bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-300/50 dark:border-gray-700/50 rounded-md px-3 py-2 outline-none transition-colors focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20"
																placeholder={$i18n.t('Example: ALL')}
																bind:value={LDAP_SERVER.ciphers}
															/>
														</Tooltip>
													</div>
													<div class="w-full"></div>
												</div>
											{/if}
										</div>
									</div>
								{/if}
							</div>
						</div>
					</div>
				</div>

				<!-- Features Section -->
				<div class="mb-3 bg-gradient-to-b from-gray-50/50 to-transparent dark:from-gray-800/20 dark:to-transparent rounded-xl p-5 border border-gray-200/60 dark:border-gray-700/30">
					<div class="mb-4 flex items-center gap-2">
						<div class="w-1 h-6 bg-gradient-to-b from-amber-500 to-red-500 rounded-sm"></div>
						<div class="text-base font-semibold text-gray-900 dark:text-gray-100" style="letter-spacing: -0.01em;">{$i18n.t('Features')}</div>
					</div>

					<div class="space-y-3 bg-white dark:bg-gray-800/50 rounded-lg p-4 shadow-sm border border-gray-200/80 dark:border-gray-700/50">
						<!-- Enable Community Sharing -->
						<div class="flex w-full items-center justify-between py-2 border-b border-gray-200/60 dark:border-gray-700/40">
							<div class="self-center text-sm font-medium text-gray-800 dark:text-gray-200">
								{$i18n.t('Enable Community Sharing')}
							</div>
							<Switch bind:state={adminConfig.ENABLE_COMMUNITY_SHARING} />
						</div>

						<!-- Enable Message Rating -->
						<div class="flex w-full items-center justify-between py-2 border-b border-gray-200/60 dark:border-gray-700/40">
							<div class="self-center text-sm font-medium text-gray-800 dark:text-gray-200">{$i18n.t('Enable Message Rating')}</div>
							<Switch bind:state={adminConfig.ENABLE_MESSAGE_RATING} />
						</div>

						<!-- Channels -->
						<div class="flex w-full items-center justify-between py-2 border-b border-gray-200/60 dark:border-gray-700/40">
							<div class="self-center text-sm font-medium text-gray-800 dark:text-gray-200">
								{$i18n.t('Channels')} <span class="bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 px-1.5 py-0.5 rounded text-[10px] font-bold ml-1">({$i18n.t('Beta')})</span>
							</div>
							<Switch bind:state={adminConfig.ENABLE_CHANNELS} />
						</div>

						<!-- User Webhooks -->
						<div class="flex w-full items-center justify-between py-2 border-b border-gray-200/60 dark:border-gray-700/40">
							<div class="self-center text-sm font-medium text-gray-800 dark:text-gray-200">
								{$i18n.t('User Webhooks')}
							</div>
							<Switch bind:state={adminConfig.ENABLE_USER_WEBHOOKS} />
						</div>

						<!-- WebUI URL -->
						<div class="w-full justify-between py-3 border-b border-gray-200/60 dark:border-gray-700/40">
							<div class="flex w-full justify-between mb-2">
								<div class="self-center text-sm font-semibold text-gray-800 dark:text-gray-200">{$i18n.t('WebUI URL')}</div>
							</div>

							<div class="flex space-x-2">
								<input
									class="w-full rounded-lg py-2.5 px-3.5 text-sm bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 border border-gray-300/50 dark:border-gray-600/50 outline-none transition-colors focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20"
									type="text"
									placeholder={`e.g.) "http://localhost:3000"`}
									bind:value={adminConfig.WEBUI_URL}
								/>
							</div>

							<div class="mt-2 text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
								{$i18n.t(
									'Enter the public URL of your WebUI. This URL will be used to generate links in the notifications.'
								)}
							</div>
						</div>

						<!-- Webhook URL -->
						<div class="w-full justify-between py-3">
							<div class="flex w-full justify-between mb-2">
								<div class="self-center text-sm font-semibold text-gray-800 dark:text-gray-200">{$i18n.t('Webhook URL')}</div>
							</div>

							<div class="flex space-x-2">
								<input
									class="w-full rounded-lg py-2.5 px-3.5 text-sm bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 border border-gray-300/50 dark:border-gray-600/50 outline-none transition-colors focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20"
									type="text"
									placeholder={`https://example.com/webhook`}
									bind:value={webhookUrl}
								/>
							</div>
						</div>
					</div>
				</div>
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-4 text-sm font-medium border-t border-gray-200 dark:border-gray-700/50">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-orange-600 hover:bg-orange-700 text-white transition rounded-lg"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>