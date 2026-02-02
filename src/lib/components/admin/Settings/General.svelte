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
				<div class="mb-6" style="background: linear-gradient(to bottom, rgba(0,0,0,0.02), transparent); border-radius: 12px; padding: 20px; border: 1px solid rgba(0,0,0,0.05);">
					<div class="mb-4" style="display: flex; align-items: center; gap: 8px;">
						<div style="width: 4px; height: 24px; background: linear-gradient(to bottom, #3b82f6, #8b5cf6); border-radius: 2px;"></div>
						<div class="text-base font-medium" style="color: #1f2937; letter-spacing: -0.01em;">{$i18n.t('General')}</div>
					</div>

					<!-- Version Info Card -->
					<div class="mb-4" style="background: white; border-radius: 10px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid rgba(0,0,0,0.06);">
						<div class="mb-2 text-xs font-medium flex space-x-2 items-center" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
							<div>{$i18n.t('Version')}</div>
						</div>
						<div class="flex w-full justify-between items-center">
							<div class="flex flex-col text-xs text-gray-700 dark:text-gray-200" style="gap: 6px;">
								<div class="flex gap-1" style="align-items: center;">
									<Tooltip content={WEBUI_BUILD_HASH}>
										<span style="font-family: 'JetBrains Mono', monospace; background: #f3f4f6; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; color: #374151;">v{WEBUI_VERSION}</span>
									</Tooltip>

									<a
										href="https://github.com/open-webui/open-webui/releases/tag/v{version.latest}"
										target="_blank"
										style="color: #3b82f6; font-weight: 500; transition: color 0.2s;"
									>
										{updateAvailable === null
											? $i18n.t('Checking for updates...')
											: updateAvailable
												? `(v${version.latest} ${$i18n.t('available!')})`
												: $i18n.t('(latest)')}
									</a>
								</div>

								<button
									class="underline flex items-center space-x-1 text-xs text-gray-500 dark:text-gray-500"
									type="button"
									on:click={() => {
										showChangelog.set(true);
									}}
									style="transition: color 0.2s; width: fit-content;"
								>
									<div>{$i18n.t("See what's new")}</div>
								</button>
							</div>

							<button
								class="text-xs px-3 py-1.5 bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-lg font-medium"
								type="button"
								on:click={() => {
									checkForVersionUpdates();
								}}
								style="box-shadow: 0 1px 2px rgba(0,0,0,0.05); border: 1px solid rgba(0,0,0,0.08); font-weight: 600;"
							>
								{$i18n.t('Check for updates')}
							</button>
						</div>
					</div>

					<!-- Help Card -->
					<div class="mb-4" style="background: white; border-radius: 10px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid rgba(0,0,0,0.06);">
						<div class="flex w-full justify-between items-center">
							<div class="text-xs pr-2">
								<div class="font-medium" style="color: #1f2937; margin-bottom: 4px; font-size: 13px;">
									{$i18n.t('Help')}
								</div>
								<div class="text-xs text-gray-500" style="line-height: 1.5;">
									{$i18n.t('Discover how to use Open WebUI and seek support from the community.')}
								</div>
							</div>

							<a
								class="flex-shrink-0 text-xs font-medium underline"
								href="https://docs.openwebui.com/"
								target="_blank"
								style="color: #3b82f6; font-weight: 600; white-space: nowrap;"
							>
								{$i18n.t('Documentation')}
							</a>
						</div>

						<div class="mt-3" style="padding-top: 12px; border-top: 1px solid rgba(0,0,0,0.06);">
							<div class="flex space-x-1" style="gap: 6px;">
								<a href="https://discord.gg/5rJgQTnV4s" target="_blank" style="transition: transform 0.2s; display: inline-block;">
									<img
										alt="Discord"
										src="https://img.shields.io/badge/Discord-Open_WebUI-blue?logo=discord&logoColor=white"
										style="border-radius: 4px;"
									/>
								</a>

								<a href="https://twitter.com/OpenWebUI" target="_blank" style="transition: transform 0.2s; display: inline-block;">
									<img
										alt="X (formerly Twitter) Follow"
										src="https://img.shields.io/twitter/follow/OpenWebUI"
										style="border-radius: 4px;"
									/>
								</a>

								<a href="https://github.com/open-webui/open-webui" target="_blank" style="transition: transform 0.2s; display: inline-block;">
									<img
										alt="Github Repo"
										src="https://img.shields.io/github/stars/open-webui/open-webui?style=social&label=Star us on Github"
										style="border-radius: 4px;"
									/>
								</a>
							</div>
						</div>
					</div>

					<!-- License Card -->
					<div class="mb-2" style="background: white; border-radius: 10px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid rgba(0,0,0,0.06);">
						<div class="flex w-full justify-between items-center">
							<div class="text-xs pr-2">
								<div class="font-medium" style="color: #1f2937; margin-bottom: 4px; font-size: 13px;">
									{$i18n.t('License')}
								</div>

								{#if $config?.license_metadata}
									<a
										href="https://docs.openwebui.com/enterprise"
										target="_blank"
										class="text-gray-500 mt-0.5"
										style="line-height: 1.6;"
									>
										<span class="capitalize text-black dark:text-white"
											>{$config?.license_metadata?.type}
											license</span
										>
										registered to
										<span class="capitalize text-black dark:text-white"
											>{$config?.license_metadata?.organization_name}</span
										>
										for
										<span class="font-medium text-black dark:text-white"
											>{$config?.license_metadata?.seats ?? 'Unlimited'} users.</span
										>
									</a>
									{#if $config?.license_metadata?.html}
										<div class="mt-0.5">
											{@html DOMPurify.sanitize($config?.license_metadata?.html)}
										</div>
									{/if}
								{:else}
									<a
										class="text-xs hover:underline"
										href="https://docs.openwebui.com/enterprise"
										target="_blank"
										style="color: #6b7280; line-height: 1.6; transition: color 0.2s;"
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
				<div class="mb-6" style="background: linear-gradient(to bottom, rgba(0,0,0,0.02), transparent); border-radius: 12px; padding: 20px; border: 1px solid rgba(0,0,0,0.05);">
					<div class="mb-4" style="display: flex; align-items: center; gap: 8px;">
						<div style="width: 4px; height: 24px; background: linear-gradient(to bottom, #10b981, #06b6d4); border-radius: 2px;"></div>
						<div class="text-base font-medium" style="color: #1f2937; letter-spacing: -0.01em;">{$i18n.t('Authentication')}</div>
					</div>

					<div class="space-y-3" style="background: white; border-radius: 10px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid rgba(0,0,0,0.06);">
						<!-- Default User Role -->
						<div class="flex w-full justify-between items-center" style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
							<div class="self-center text-xs font-medium" style="color: #374151; font-size: 13px;">{$i18n.t('Default User Role')}</div>
							<div class="flex items-center relative">
								<select
									class="dark:bg-gray-900 w-fit pr-8 rounded-sm px-2 text-xs bg-transparent outline-hidden text-right"
									bind:value={adminConfig.DEFAULT_USER_ROLE}
									placeholder="Select a role"
									style="background: #f9fafb; border: 1px solid rgba(0,0,0,0.1); border-radius: 6px; padding: 6px 12px; font-weight: 500; cursor: pointer; transition: all 0.2s;"
								>
									<option value="pending">{$i18n.t('pending')}</option>
									<option value="user">{$i18n.t('user')}</option>
									<option value="admin">{$i18n.t('admin')}</option>
								</select>
							</div>
						</div>

						<!-- Enable New Sign Ups -->
						<div class="flex w-full justify-between items-center" style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
							<div class="self-center text-xs font-medium" style="color: #374151; font-size: 13px;">{$i18n.t('Enable New Sign Ups')}</div>
							<Switch bind:state={adminConfig.ENABLE_SIGNUP} />
						</div>

						<!-- Show Admin Details -->
						<div class="flex w-full items-center justify-between" style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
							<div class="self-center text-xs font-medium" style="color: #374151; font-size: 13px;">
								{$i18n.t('Show Admin Details in Account Pending Overlay')}
							</div>
							<Switch bind:state={adminConfig.SHOW_ADMIN_DETAILS} />
						</div>

						<!-- Enable API Key -->
						<div class="flex w-full justify-between items-center" style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
							<div class="self-center text-xs font-medium" style="color: #374151; font-size: 13px;">{$i18n.t('Enable API Key')}</div>
							<Switch bind:state={adminConfig.ENABLE_API_KEY} />
						</div>

						{#if adminConfig?.ENABLE_API_KEY}
							<div class="flex w-full justify-between items-center" style="padding: 8px 0; padding-left: 16px; border-bottom: 1px solid rgba(0,0,0,0.04); border-left: 3px solid #3b82f6;">
								<div class="self-center text-xs font-medium" style="color: #374151; font-size: 13px;">
									{$i18n.t('API Key Endpoint Restrictions')}
								</div>
								<Switch bind:state={adminConfig.ENABLE_API_KEY_ENDPOINT_RESTRICTIONS} />
							</div>

							{#if adminConfig?.ENABLE_API_KEY_ENDPOINT_RESTRICTIONS}
								<div class="flex w-full flex-col" style="padding: 12px 0; padding-left: 16px; border-left: 3px solid #3b82f6;">
									<div class="text-xs font-medium" style="color: #374151; margin-bottom: 8px; font-size: 13px;">
										{$i18n.t('Allowed Endpoints')}
									</div>

									<input
										class="w-full rounded-lg text-sm dark:text-gray-300 bg-transparent outline-hidden"
										type="text"
										placeholder={`e.g.) /api/v1/messages, /api/v1/channels`}
										bind:value={adminConfig.API_KEY_ALLOWED_ENDPOINTS}
										style="background: #f9fafb; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
									/>

									<div class="mt-2 text-xs text-gray-400 dark:text-gray-500" style="line-height: 1.5;">
										<a
											href="https://docs.openwebui.com/getting-started/api-endpoints"
											target="_blank"
											class="text-gray-300 font-medium underline"
											style="color: #3b82f6; transition: color 0.2s;"
										>
											{$i18n.t('To learn more about available endpoints, visit our documentation.')}
										</a>
									</div>
								</div>
							{/if}
						{/if}

						<!-- JWT Expiration -->
						<div class="w-full justify-between" style="padding: 12px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
							<div class="flex w-full justify-between">
								<div class="self-center text-xs font-medium" style="color: #374151; margin-bottom: 8px; font-size: 13px;">{$i18n.t('JWT Expiration')}</div>
							</div>

							<div class="flex space-x-2">
								<input
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
									type="text"
									placeholder={`e.g.) "30m","1h", "10d". `}
									bind:value={adminConfig.JWT_EXPIRES_IN}
									style="background: #f9fafb; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
								/>
							</div>

							<div class="mt-2 text-xs text-gray-400 dark:text-gray-500" style="line-height: 1.5;">
								{$i18n.t('Valid time units:')}
								<span class="text-gray-300 font-medium" style="color: #374151; font-weight: 600;"
									>{$i18n.t("'s', 'm', 'h', 'd', 'w' or '-1' for no expiration.")}</span
								>
							</div>
						</div>

						<!-- LDAP Section -->
						<div class="space-y-3" style="padding-top: 8px;">
							<div class="space-y-2">
								<div class="flex justify-between items-center text-sm" style="padding: 8px 0;">
									<div class="font-medium" style="color: #374151; font-size: 13px;">{$i18n.t('LDAP')}</div>
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
									<div class="flex flex-col gap-1" style="background: #f9fafb; border-radius: 8px; padding: 16px; border: 1px solid rgba(0,0,0,0.08);">
										<div class="flex w-full gap-2">
											<div class="w-full">
												<div class="self-center text-xs font-medium min-w-fit mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
													{$i18n.t('Label')}
												</div>
												<input
													class="w-full bg-transparent outline-hidden py-0.5"
													required
													placeholder={$i18n.t('Enter server label')}
													bind:value={LDAP_SERVER.label}
													style="background: white; border: 1px solid rgba(0,0,0,0.1); border-radius: 6px; padding: 8px 12px; transition: all 0.2s;"
												/>
											</div>
											<div class="w-full"></div>
										</div>
										<div class="flex w-full gap-2" style="margin-top: 12px;">
											<div class="w-full">
												<div class="self-center text-xs font-medium min-w-fit mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
													{$i18n.t('Host')}
												</div>
												<input
													class="w-full bg-transparent outline-hidden py-0.5"
													required
													placeholder={$i18n.t('Enter server host')}
													bind:value={LDAP_SERVER.host}
													style="background: white; border: 1px solid rgba(0,0,0,0.1); border-radius: 6px; padding: 8px 12px; transition: all 0.2s;"
												/>
											</div>
											<div class="w-full">
												<div class="self-center text-xs font-medium min-w-fit mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
													{$i18n.t('Port')}
												</div>
												<Tooltip
													placement="top-start"
													content={$i18n.t('Default to 389 or 636 if TLS is enabled')}
													className="w-full"
												>
													<input
														class="w-full bg-transparent outline-hidden py-0.5"
														type="number"
														placeholder={$i18n.t('Enter server port')}
														bind:value={LDAP_SERVER.port}
														style="background: white; border: 1px solid rgba(0,0,0,0.1); border-radius: 6px; padding: 8px 12px; transition: all 0.2s;"
													/>
												</Tooltip>
											</div>
										</div>
										<div class="flex w-full gap-2" style="margin-top: 12px;">
											<div class="w-full">
												<div class="self-center text-xs font-medium min-w-fit mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
													{$i18n.t('Application DN')}
												</div>
												<Tooltip
													content={$i18n.t('The Application Account DN you bind with for search')}
													placement="top-start"
												>
													<input
														class="w-full bg-transparent outline-hidden py-0.5"
														required
														placeholder={$i18n.t('Enter Application DN')}
														bind:value={LDAP_SERVER.app_dn}
														style="background: white; border: 1px solid rgba(0,0,0,0.1); border-radius: 6px; padding: 8px 12px; transition: all 0.2s;"
													/>
												</Tooltip>
											</div>
											<div class="w-full">
												<div class="self-center text-xs font-medium min-w-fit mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
													{$i18n.t('Application DN Password')}
												</div>
												<SensitiveInput
													placeholder={$i18n.t('Enter Application DN Password')}
													bind:value={LDAP_SERVER.app_dn_password}
												/>
											</div>
										</div>
										<div class="flex w-full gap-2" style="margin-top: 12px;">
											<div class="w-full">
												<div class="self-center text-xs font-medium min-w-fit mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
													{$i18n.t('Attribute for Mail')}
												</div>
												<Tooltip
													content={$i18n.t(
														'The LDAP attribute that maps to the mail that users use to sign in.'
													)}
													placement="top-start"
												>
													<input
														class="w-full bg-transparent outline-hidden py-0.5"
														required
														placeholder={$i18n.t('Example: mail')}
														bind:value={LDAP_SERVER.attribute_for_mail}
														style="background: white; border: 1px solid rgba(0,0,0,0.1); border-radius: 6px; padding: 8px 12px; transition: all 0.2s;"
													/>
												</Tooltip>
											</div>
										</div>
										<div class="flex w-full gap-2" style="margin-top: 12px;">
											<div class="w-full">
												<div class="self-center text-xs font-medium min-w-fit mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
													{$i18n.t('Attribute for Username')}
												</div>
												<Tooltip
													content={$i18n.t(
														'The LDAP attribute that maps to the username that users use to sign in.'
													)}
													placement="top-start"
												>
													<input
														class="w-full bg-transparent outline-hidden py-0.5"
														required
														placeholder={$i18n.t(
															'Example: sAMAccountName or uid or userPrincipalName'
														)}
														bind:value={LDAP_SERVER.attribute_for_username}
														style="background: white; border: 1px solid rgba(0,0,0,0.1); border-radius: 6px; padding: 8px 12px; transition: all 0.2s;"
													/>
												</Tooltip>
											</div>
										</div>
										<div class="flex w-full gap-2" style="margin-top: 12px;">
											<div class="w-full">
												<div class="self-center text-xs font-medium min-w-fit mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
													{$i18n.t('Search Base')}
												</div>
												<Tooltip
													content={$i18n.t('The base to search for users')}
													placement="top-start"
												>
													<input
														class="w-full bg-transparent outline-hidden py-0.5"
														required
														placeholder={$i18n.t('Example: ou=users,dc=foo,dc=example')}
														bind:value={LDAP_SERVER.search_base}
														style="background: white; border: 1px solid rgba(0,0,0,0.1); border-radius: 6px; padding: 8px 12px; transition: all 0.2s;"
													/>
												</Tooltip>
											</div>
										</div>
										<div class="flex w-full gap-2" style="margin-top: 12px;">
											<div class="w-full">
												<div class="self-center text-xs font-medium min-w-fit mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
													{$i18n.t('Search Filters')}
												</div>
												<input
													class="w-full bg-transparent outline-hidden py-0.5"
													placeholder={$i18n.t('Example: (&(objectClass=inetOrgPerson)(uid=%s))')}
													bind:value={LDAP_SERVER.search_filters}
													style="background: white; border: 1px solid rgba(0,0,0,0.1); border-radius: 6px; padding: 8px 12px; transition: all 0.2s;"
												/>
											</div>
										</div>
										<div class="text-xs text-gray-400 dark:text-gray-500" style="margin-top: 8px; line-height: 1.5;">
											<a
												class="text-gray-300 font-medium underline"
												href="https://ldap.com/ldap-filters/"
												target="_blank"
												style="color: #3b82f6; transition: color 0.2s;"
											>
												{$i18n.t('Click here for filter guides.')}
											</a>
										</div>
										<div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(0,0,0,0.08);">
											<div class="flex justify-between items-center text-sm">
												<div class="font-medium" style="color: #374151; font-size: 13px;">{$i18n.t('TLS')}</div>
												<div class="mt-1">
													<Switch bind:state={LDAP_SERVER.use_tls} />
												</div>
											</div>
											{#if LDAP_SERVER.use_tls}
												<div class="flex w-full gap-2" style="margin-top: 12px;">
													<div class="w-full">
														<div class="self-center text-xs font-medium min-w-fit mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
															{$i18n.t('Certificate Path')}
														</div>
														<input
															class="w-full bg-transparent outline-hidden py-0.5"
															placeholder={$i18n.t('Enter certificate path')}
															bind:value={LDAP_SERVER.certificate_path}
															style="background: white; border: 1px solid rgba(0,0,0,0.1); border-radius: 6px; padding: 8px 12px; transition: all 0.2s;"
														/>
													</div>
												</div>
												<div class="flex w-full gap-2" style="margin-top: 12px;">
													<div class="w-full">
														<div class="self-center text-xs font-medium min-w-fit mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
															{$i18n.t('Ciphers')}
														</div>
														<Tooltip content={$i18n.t('Default to ALL')} placement="top-start">
															<input
																class="w-full bg-transparent outline-hidden py-0.5"
																placeholder={$i18n.t('Example: ALL')}
																bind:value={LDAP_SERVER.ciphers}
																style="background: white; border: 1px solid rgba(0,0,0,0.1); border-radius: 6px; padding: 8px 12px; transition: all 0.2s;"
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
				<div class="mb-3" style="background: linear-gradient(to bottom, rgba(0,0,0,0.02), transparent); border-radius: 12px; padding: 20px; border: 1px solid rgba(0,0,0,0.05);">
					<div class="mb-4" style="display: flex; align-items: center; gap: 8px;">
						<div style="width: 4px; height: 24px; background: linear-gradient(to bottom, #f59e0b, #ef4444); border-radius: 2px;"></div>
						<div class="text-base font-medium" style="color: #1f2937; letter-spacing: -0.01em;">{$i18n.t('Features')}</div>
					</div>

					<div class="space-y-3" style="background: white; border-radius: 10px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid rgba(0,0,0,0.06);">
						<!-- Enable Community Sharing -->
						<div class="flex w-full items-center justify-between" style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
							<div class="self-center text-xs font-medium" style="color: #374151; font-size: 13px;">
								{$i18n.t('Enable Community Sharing')}
							</div>
							<Switch bind:state={adminConfig.ENABLE_COMMUNITY_SHARING} />
						</div>

						<!-- Enable Message Rating -->
						<div class="flex w-full items-center justify-between" style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
							<div class="self-center text-xs font-medium" style="color: #374151; font-size: 13px;">{$i18n.t('Enable Message Rating')}</div>
							<Switch bind:state={adminConfig.ENABLE_MESSAGE_RATING} />
						</div>

						<!-- Channels -->
						<div class="flex w-full items-center justify-between" style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
							<div class="self-center text-xs font-medium" style="color: #374151; font-size: 13px;">
								{$i18n.t('Channels')} <span style="background: #dbeafe; color: #1e40af; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 700; margin-left: 4px;">({$i18n.t('Beta')})</span>
							</div>
							<Switch bind:state={adminConfig.ENABLE_CHANNELS} />
						</div>

						<!-- User Webhooks -->
						<div class="flex w-full items-center justify-between" style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
							<div class="self-center text-xs font-medium" style="color: #374151; font-size: 13px;">
								{$i18n.t('User Webhooks')}
							</div>
							<Switch bind:state={adminConfig.ENABLE_USER_WEBHOOKS} />
						</div>

						<!-- WebUI URL -->
						<div class="w-full justify-between" style="padding: 12px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
							<div class="flex w-full justify-between">
								<div class="self-center text-xs font-medium" style="color: #374151; margin-bottom: 8px; font-size: 13px;">{$i18n.t('WebUI URL')}</div>
							</div>

							<div class="flex space-x-2">
								<input
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
									type="text"
									placeholder={`e.g.) "http://localhost:3000"`}
									bind:value={adminConfig.WEBUI_URL}
									style="background: #f9fafb; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
								/>
							</div>

							<div class="mt-2 text-xs text-gray-400 dark:text-gray-500" style="line-height: 1.5;">
								{$i18n.t(
									'Enter the public URL of your WebUI. This URL will be used to generate links in the notifications.'
								)}
							</div>
						</div>

						<!-- Webhook URL -->
						<div class="w-full justify-between" style="padding: 12px 0;">
							<div class="flex w-full justify-between">
								<div class="self-center text-xs font-medium" style="color: #374151; margin-bottom: 8px; font-size: 13px;">{$i18n.t('Webhook URL')}</div>
							</div>

							<div class="flex space-x-2">
								<input
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
									type="text"
									placeholder={`https://example.com/webhook`}
									bind:value={webhookUrl}
									style="background: #f9fafb; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
								/>
							</div>
						</div>
					</div>
				</div>
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium" style="border-top: 1px solid rgba(0,0,0,0.08); margin-top: 8px; padding-top: 16px;">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
			style="background: linear-gradient(135deg, #3b82f6, #8b5cf6); box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3); padding: 10px 24px; font-weight: 600; transition: all 0.3s; border: none;"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>