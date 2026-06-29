<script lang="ts">
	import { getBackendConfig } from '$lib/apis';
	import {
		getAdminConfig,
		getLdapConfig,
		getLdapServer,
		getOAuthConfig,
		updateLdapConfig,
		updateLdapServer,
		updateOAuthConfig,
		updateAdminConfig
	} from '$lib/apis/auths';
	import { getGroups } from '$lib/apis/groups';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { config } from '$lib/stores';
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	let adminConfig = null;
	let groups = [];

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

	let oauthConfig: any = null;

	const updateLdapServerHandler = async () => {
		await updateLdapConfig(localStorage.token, ENABLE_LDAP);
		if (!ENABLE_LDAP) return true;

		const res = await updateLdapServer(localStorage.token, LDAP_SERVER).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		return !!res;
	};

	const updateOAuthHandler = async () => {
		if (!oauthConfig) return true;
		const res = await updateOAuthConfig(localStorage.token, oauthConfig).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (res) {
			oauthConfig = res;
		}
		return !!res;
	};

	const updateAdminHandler = async () => {
		if (!adminConfig) return true;
		const res = await updateAdminConfig(localStorage.token, adminConfig).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		return !!res;
	};

	const submitHandler = async () => {
		const adminSaved = await updateAdminHandler();
		const ldapSaved = await updateLdapServerHandler();
		const oauthSaved = await updateOAuthHandler();

		if (adminSaved && ldapSaved && oauthSaved) {
			toast.success($i18n.t('Settings saved successfully!'));
			await config.set(await getBackendConfig());
		}
	};

	onMount(async () => {
		await Promise.all([
			(async () => {
				adminConfig = await getAdminConfig(localStorage.token);
			})(),
			(async () => {
				groups = await getGroups(localStorage.token);
			})(),
			(async () => {
				LDAP_SERVER = await getLdapServer(localStorage.token);
			})(),
			(async () => {
				oauthConfig = await getOAuthConfig(localStorage.token).catch(() => null);
			})()
		]);

		const ldapConfig = await getLdapConfig(localStorage.token);
		ENABLE_LDAP = ldapConfig.ENABLE_LDAP;
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={submitHandler}
>
	<div class="space-y-3 overflow-y-scroll scrollbar-hidden h-full">
		{#if adminConfig !== null}
			<div class="mb-3">
				<div class="mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('User Access')}</div>

				<hr class="border-gray-100/30 dark:border-gray-850/30 my-2" />

				<div class="  mb-2.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">{$i18n.t('Default User Role')}</div>
					<div class="flex items-center relative">
						<select
							class="w-fit pr-8 rounded-sm px-2 text-xs bg-transparent outline-hidden text-right"
							bind:value={adminConfig.DEFAULT_USER_ROLE}
							placeholder={$i18n.t('Select a role')}
						>
							<option value="pending">{$i18n.t('pending')}</option>
							<option value="user">{$i18n.t('user')}</option>
							<option value="admin">{$i18n.t('admin')}</option>
						</select>
					</div>
				</div>

				<div class="  mb-2.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">{$i18n.t('Default Group')}</div>
					<div class="flex items-center relative max-w-48">
						<select
							class="w-full pr-8 rounded-sm px-2 text-xs bg-transparent outline-hidden text-right truncate"
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

				<div class=" mb-2.5 flex w-full justify-between pr-2">
					<div class=" self-center text-xs font-medium">{$i18n.t('Enable New Sign Ups')}</div>

					<Switch bind:state={adminConfig.ENABLE_SIGNUP} />
				</div>

				<div class="mb-2.5 flex w-full justify-between pr-2">
					<div class=" self-center text-xs font-medium">{$i18n.t('Enable API Keys')}</div>

					<Switch bind:state={adminConfig.ENABLE_API_KEYS} />
				</div>

				{#if adminConfig?.ENABLE_API_KEYS}
					<div class="mb-2.5 flex w-full justify-between pr-2">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('API Key Endpoint Restrictions')}
						</div>

						<Switch bind:state={adminConfig.ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS} />
					</div>

					{#if adminConfig?.ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS}
						<div class=" flex w-full flex-col pr-2 mb-2.5">
							<div class=" text-xs font-medium">
								{$i18n.t('Allowed Endpoints')}
							</div>

							<input
								class="w-full mt-1 text-sm dark:text-gray-300 bg-transparent outline-hidden"
								type="text"
								placeholder={`e.g.) /api/v1/messages, /api/v1/channels`}
								bind:value={adminConfig.API_KEYS_ALLOWED_ENDPOINTS}
							/>

							<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
								<a
									href="https://docs.openwebui.com/reference/api-endpoints"
									target="_blank"
									class=" text-gray-300 font-medium underline"
								>
									{$i18n.t('To learn more about available endpoints, visit our documentation.')}
								</a>
							</div>
						</div>
					{/if}
				{/if}

				<div class=" mb-2.5 w-full justify-between">
					<div class="flex w-full justify-between">
						<div class=" self-center text-xs font-medium">{$i18n.t('JWT Expiration')}</div>
					</div>

					<div class="flex mt-2 space-x-2">
						<input
							class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
							type="text"
							placeholder={`e.g.) "30m","1h", "10d". `}
							bind:value={adminConfig.JWT_EXPIRES_IN}
						/>
					</div>

					<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
						{$i18n.t('Valid time units:')}
						<span class=" text-gray-300 font-medium"
							>{$i18n.t("'s', 'm', 'h', 'd', 'w' or '-1' for no expiration.")}</span
						>
					</div>

					{#if adminConfig.JWT_EXPIRES_IN === '-1'}
						<div class="mt-2 text-xs">
							<div
								class=" bg-yellow-500/20 text-yellow-700 dark:text-yellow-200 rounded-lg px-3 py-2"
							>
								<div>
									<span class=" font-medium">{$i18n.t('Warning')}:</span>
									<span
										><a
											href="https://docs.openwebui.com/reference/env-configuration#jwt_expires_in"
											target="_blank"
											class=" underline"
											>{$i18n.t('No expiration can pose security risks.')}
										</a></span
									>
								</div>
							</div>
						</div>
					{/if}
				</div>
				<div class=" mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('Pending Accounts')}</div>

				<hr class=" border-gray-100/30 dark:border-gray-850/30 my-2" />

				<div class="mb-2.5 flex w-full items-center justify-between pr-2">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Show Admin Details in Account Pending Overlay')}
					</div>

					<Switch bind:state={adminConfig.SHOW_ADMIN_DETAILS} />
				</div>

				{#if adminConfig.SHOW_ADMIN_DETAILS}
					<div class="mb-2.5 w-full justify-between">
						<div class="flex w-full justify-between">
							<div class=" self-center text-xs font-medium">{$i18n.t('Admin Contact Email')}</div>
						</div>

						<div class="flex mt-2 space-x-2">
							<input
								class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
								type="email"
								placeholder={$i18n.t('Leave empty to use first admin user')}
								bind:value={adminConfig.ADMIN_EMAIL}
							/>
						</div>
					</div>
				{/if}

				<div class="mb-2.5">
					<div class=" self-center text-xs font-medium mb-2">
						{$i18n.t('Pending User Overlay Title')}
					</div>
					<Textarea
						placeholder={$i18n.t(
							'Enter a title for the pending user info overlay. Leave empty for default.'
						)}
						bind:value={adminConfig.PENDING_USER_OVERLAY_TITLE}
					/>
				</div>

				<div class="mb-2.5">
					<div class=" self-center text-xs font-medium mb-2">
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
		{/if}

		<div class=" space-y-3">
			<div class="mt-2 space-y-2 pr-1.5">
				<div class="flex justify-between items-center text-sm">
					<div class="  font-medium">{$i18n.t('LDAP')}</div>

					<div class="mt-1">
						<Switch bind:state={ENABLE_LDAP} />
					</div>
				</div>

				{#if ENABLE_LDAP}
					<div class="flex flex-col gap-1">
						<div class="flex w-full gap-2">
							<div class="w-full">
								<div class=" self-center text-xs font-medium min-w-fit mb-1">
									{$i18n.t('Label')}
								</div>
								<input
									class="w-full bg-transparent outline-hidden py-0.5"
									required
									placeholder={$i18n.t('Enter server label')}
									bind:value={LDAP_SERVER.label}
								/>
							</div>
							<div class="w-full"></div>
						</div>
						<div class="flex w-full gap-2">
							<div class="w-full">
								<div class=" self-center text-xs font-medium min-w-fit mb-1">
									{$i18n.t('Host')}
								</div>
								<input
									class="w-full bg-transparent outline-hidden py-0.5"
									required
									placeholder={$i18n.t('Enter server host')}
									bind:value={LDAP_SERVER.host}
								/>
							</div>
							<div class="w-full">
								<div class=" self-center text-xs font-medium min-w-fit mb-1">
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
									/>
								</Tooltip>
							</div>
						</div>
						<div class="flex w-full gap-2">
							<div class="w-full">
								<div class=" self-center text-xs font-medium min-w-fit mb-1">
									{$i18n.t('Application DN')}
								</div>
								<Tooltip
									content={$i18n.t('The Application Account DN you bind with for search')}
									placement="top-start"
								>
									<input
										class="w-full bg-transparent outline-hidden py-0.5"
										placeholder={$i18n.t('Enter Application DN')}
										bind:value={LDAP_SERVER.app_dn}
									/>
								</Tooltip>
							</div>
							<div class="w-full">
								<div class=" self-center text-xs font-medium min-w-fit mb-1">
									{$i18n.t('Application DN Password')}
								</div>
								<SensitiveInput
									placeholder={$i18n.t('Enter Application DN Password')}
									required={false}
									bind:value={LDAP_SERVER.app_dn_password}
								/>
							</div>
						</div>
						<div class="flex w-full gap-2">
							<div class="w-full">
								<div class=" self-center text-xs font-medium min-w-fit mb-1">
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
									/>
								</Tooltip>
							</div>
						</div>
						<div class="flex w-full gap-2">
							<div class="w-full">
								<div class=" self-center text-xs font-medium min-w-fit mb-1">
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
										placeholder={$i18n.t('Example: sAMAccountName or uid or userPrincipalName')}
										bind:value={LDAP_SERVER.attribute_for_username}
									/>
								</Tooltip>
							</div>
						</div>
						<div class="flex w-full gap-2">
							<div class="w-full">
								<div class=" self-center text-xs font-medium min-w-fit mb-1">
									{$i18n.t('Search Base')}
								</div>
								<Tooltip content={$i18n.t('The base to search for users')} placement="top-start">
									<input
										class="w-full bg-transparent outline-hidden py-0.5"
										required
										placeholder={$i18n.t('Example: ou=users,dc=foo,dc=example')}
										bind:value={LDAP_SERVER.search_base}
									/>
								</Tooltip>
							</div>
						</div>
						<div class="flex w-full gap-2">
							<div class="w-full">
								<div class=" self-center text-xs font-medium min-w-fit mb-1">
									{$i18n.t('Search Filters')}
								</div>
								<input
									class="w-full bg-transparent outline-hidden py-0.5"
									placeholder={$i18n.t('Example: (&(objectClass=inetOrgPerson)(uid=%s))')}
									bind:value={LDAP_SERVER.search_filters}
								/>
							</div>
						</div>
						<div class="text-xs text-gray-400 dark:text-gray-500">
							<a
								class=" text-gray-300 font-medium underline"
								href="https://ldap.com/ldap-filters/"
								target="_blank"
							>
								{$i18n.t('Click here for filter guides.')}
							</a>
						</div>
						<div>
							<div class="flex justify-between items-center text-sm">
								<div class="  font-medium">{$i18n.t('TLS')}</div>

								<div class="mt-1">
									<Switch bind:state={LDAP_SERVER.use_tls} />
								</div>
							</div>
							{#if LDAP_SERVER.use_tls}
								<div class="flex w-full gap-2">
									<div class="w-full">
										<div class=" self-center text-xs font-medium min-w-fit mb-1 mt-1">
											{$i18n.t('Certificate Path')}
										</div>
										<input
											class="w-full bg-transparent outline-hidden py-0.5"
											placeholder={$i18n.t('Enter certificate path')}
											bind:value={LDAP_SERVER.certificate_path}
										/>
									</div>
								</div>
								<div class="flex justify-between items-center text-xs">
									<div class=" font-medium">{$i18n.t('Validate certificate')}</div>

									<div class="mt-1">
										<Switch bind:state={LDAP_SERVER.validate_cert} />
									</div>
								</div>
								<div class="flex w-full gap-2">
									<div class="w-full">
										<div class=" self-center text-xs font-medium min-w-fit mb-1">
											{$i18n.t('Ciphers')}
										</div>
										<Tooltip content={$i18n.t('Default to ALL')} placement="top-start">
											<input
												class="w-full bg-transparent outline-hidden py-0.5"
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
		{#if oauthConfig}
			<div class="mb-3">
				<div class="mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('OAuth / OIDC')}</div>

				<hr class="border-gray-100/30 dark:border-gray-850/30 my-2" />

				<div class="pr-1.5">
					<div class="space-y-3">
						<div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
							<div class="w-full">
								<div class="self-center text-xs font-medium min-w-fit mb-1">
									{$i18n.t('Provider Name')}
								</div>
								<input
									class="w-full bg-transparent outline-hidden py-0.5"
									placeholder="SSO"
									bind:value={oauthConfig.OAUTH_PROVIDER_NAME}
								/>
							</div>
							<div class="w-full">
								<div class="self-center text-xs font-medium min-w-fit mb-1">
									{$i18n.t('Provider URL')}
								</div>
								<input
									class="w-full bg-transparent outline-hidden py-0.5"
									placeholder="https://accounts.google.com/.well-known/openid-configuration"
									bind:value={oauthConfig.OPENID_PROVIDER_URL}
								/>
							</div>
						</div>

						<div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
							<div class="w-full">
								<div class="self-center text-xs font-medium min-w-fit mb-1">
									{$i18n.t('Client ID')}
								</div>
								<input
									class="w-full bg-transparent outline-hidden py-0.5"
									placeholder={$i18n.t('Enter Client ID')}
									bind:value={oauthConfig.OAUTH_CLIENT_ID}
								/>
							</div>
							<div class="w-full">
								<div class="self-center text-xs font-medium min-w-fit mb-1">
									{$i18n.t('Client Secret')}
								</div>
								<SensitiveInput
									placeholder={$i18n.t('Enter Client Secret')}
									required={false}
									outerClassName="flex flex-1 bg-transparent"
									inputClassName="w-full text-sm py-0.5 bg-transparent"
									bind:value={oauthConfig.OAUTH_CLIENT_SECRET}
								/>
							</div>
						</div>

						<div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
							<div class="w-full">
								<div class="self-center text-xs font-medium min-w-fit mb-1">
									{$i18n.t('Redirect URI')}
								</div>
								<input
									class="w-full bg-transparent outline-hidden py-0.5"
									placeholder={$i18n.t('Enter Redirect URI')}
									bind:value={oauthConfig.OPENID_REDIRECT_URI}
								/>
							</div>
							<div class="w-full">
								<div class="self-center text-xs font-medium min-w-fit mb-1">
									{$i18n.t('Scopes')}
								</div>
								<input
									class="w-full bg-transparent outline-hidden py-0.5"
									placeholder="openid email profile"
									bind:value={oauthConfig.OAUTH_SCOPES}
								/>
							</div>
						</div>

						<div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
							<div class="w-full">
								<div class="self-center text-xs font-medium min-w-fit mb-1">
									{$i18n.t('Email Claim')}
								</div>
								<input
									class="w-full bg-transparent outline-hidden py-0.5"
									placeholder="email"
									bind:value={oauthConfig.OAUTH_EMAIL_CLAIM}
								/>
							</div>
							<div class="w-full">
								<div class="self-center text-xs font-medium min-w-fit mb-1">
									{$i18n.t('Username Claim')}
								</div>
								<input
									class="w-full bg-transparent outline-hidden py-0.5"
									placeholder="name"
									bind:value={oauthConfig.OAUTH_USERNAME_CLAIM}
								/>
							</div>
						</div>

						<div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
							<div class="w-full">
								<div class="self-center text-xs font-medium min-w-fit mb-1">
									{$i18n.t('Picture Claim')}
								</div>
								<input
									class="w-full bg-transparent outline-hidden py-0.5"
									placeholder="picture"
									bind:value={oauthConfig.OAUTH_PICTURE_CLAIM}
								/>
							</div>
							<div class="w-full">
								<div class="self-center text-xs font-medium min-w-fit mb-1">
									{$i18n.t('Sub Claim')}
								</div>
								<input
									class="w-full bg-transparent outline-hidden py-0.5"
									placeholder="sub"
									bind:value={oauthConfig.OAUTH_SUB_CLAIM}
								/>
							</div>
						</div>

						<div class="flex w-full justify-between pr-2">
							<div class="self-center text-xs font-medium">
								{$i18n.t('Enable OAuth Signup')}
							</div>
							<Switch bind:state={oauthConfig.ENABLE_OAUTH_SIGNUP} />
						</div>

						<div class="flex w-full justify-between pr-2">
							<div class="self-center text-xs font-medium">
								{$i18n.t('Merge Accounts by Email')}
							</div>
							<Switch bind:state={oauthConfig.OAUTH_MERGE_ACCOUNTS_BY_EMAIL} />
						</div>

						<div class="flex w-full justify-between pr-2">
							<div class="self-center text-xs font-medium">
								{$i18n.t('Auto Redirect')}
							</div>
							<Switch bind:state={oauthConfig.OAUTH_AUTO_REDIRECT} />
						</div>

						<div class="w-full">
							<div class="self-center text-xs font-medium min-w-fit mb-1">
								{$i18n.t('Allowed Domains')}
							</div>
							<input
								class="w-full bg-transparent outline-hidden py-0.5"
								placeholder="* (all domains)"
								bind:value={oauthConfig.OAUTH_ALLOWED_DOMAINS}
							/>
						</div>

						<div class="flex w-full justify-between pr-2">
							<div class="self-center text-xs font-medium">
								{$i18n.t('Enable Role Mapping')}
							</div>
							<Switch bind:state={oauthConfig.ENABLE_OAUTH_ROLE_MANAGEMENT} />
						</div>

						{#if oauthConfig.ENABLE_OAUTH_ROLE_MANAGEMENT}
							<div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
								<div class="w-full">
									<div class="self-center text-xs font-medium min-w-fit mb-1">
										{$i18n.t('Roles Claim')}
									</div>
									<input
										class="w-full bg-transparent outline-hidden py-0.5"
										placeholder="roles"
										bind:value={oauthConfig.OAUTH_ROLES_CLAIM}
									/>
								</div>
								<div class="w-full">
									<div class="self-center text-xs font-medium min-w-fit mb-1">
										{$i18n.t('Admin Roles')}
									</div>
									<input
										class="w-full bg-transparent outline-hidden py-0.5"
										placeholder="admin"
										bind:value={oauthConfig.OAUTH_ADMIN_ROLES}
									/>
								</div>
							</div>

							<div class="w-full">
								<div class="self-center text-xs font-medium min-w-fit mb-1">
									{$i18n.t('Allowed Roles')}
								</div>
								<input
									class="w-full bg-transparent outline-hidden py-0.5"
									placeholder="*"
									bind:value={oauthConfig.OAUTH_ALLOWED_ROLES}
								/>
							</div>
						{/if}

						<div class="flex w-full justify-between pr-2">
							<div class="self-center text-xs font-medium">
								{$i18n.t('Enable Group Mapping')}
							</div>
							<Switch bind:state={oauthConfig.ENABLE_OAUTH_GROUP_MANAGEMENT} />
						</div>

						{#if oauthConfig.ENABLE_OAUTH_GROUP_MANAGEMENT}
							<div class="flex w-full justify-between pr-2">
								<div class="self-center text-xs font-medium">
									{$i18n.t('Auto-Create Groups')}
								</div>
								<Switch bind:state={oauthConfig.ENABLE_OAUTH_GROUP_CREATION} />
							</div>

							<div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
								<div class="w-full">
									<div class="self-center text-xs font-medium min-w-fit mb-1">
										{$i18n.t('Group Claim')}
									</div>
									<input
										class="w-full bg-transparent outline-hidden py-0.5"
										placeholder="groups"
										bind:value={oauthConfig.OAUTH_GROUP_CLAIM}
									/>
								</div>
								<div class="w-full">
									<div class="self-center text-xs font-medium min-w-fit mb-1">
										{$i18n.t('Blocked Groups')}
									</div>
									<input
										class="w-full bg-transparent outline-hidden py-0.5"
										placeholder={$i18n.t('Comma-separated group names')}
										bind:value={oauthConfig.OAUTH_BLOCKED_GROUPS}
									/>
								</div>
							</div>
						{/if}

						<div class="flex w-full justify-between pr-2">
							<div class="self-center text-xs font-medium">
								{$i18n.t('Update Email')}
							</div>
							<Switch bind:state={oauthConfig.OAUTH_UPDATE_EMAIL_ON_LOGIN} />
						</div>

						<div class="flex w-full justify-between pr-2">
							<div class="self-center text-xs font-medium">
								{$i18n.t('Update Name')}
							</div>
							<Switch bind:state={oauthConfig.OAUTH_UPDATE_NAME_ON_LOGIN} />
						</div>

						<div class="flex w-full justify-between pr-2">
							<div class="self-center text-xs font-medium">
								{$i18n.t('Update Picture')}
							</div>
							<Switch bind:state={oauthConfig.OAUTH_UPDATE_PICTURE_ON_LOGIN} />
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
