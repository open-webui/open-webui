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
	import AdminSettingField from './AdminSettingField.svelte';
	import AdminSettingRow from './AdminSettingRow.svelte';
	import AdminSettingSection from './AdminSettingSection.svelte';
	import SettingsSelect from '$lib/components/common/SettingsSelect.svelte';

	const i18n: any = getContext('i18n');

	let adminConfig: any = null;
	let groups: any[] = [];

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
		validate_cert: false,
		certificate_path: '',
		ciphers: '',
		enable_group_management: false,
		enable_group_creation: false,
		attribute_for_groups: 'memberOf'
	};

	let oauthConfig: any = null;
	const inputClass =
		'w-full h-7 rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';
	const textareaClass =
		'w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';

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
				// Merge into the defaults so any key the backend omits (e.g. an
				// older backend without the group settings) keeps its default.
				LDAP_SERVER = { ...LDAP_SERVER, ...(await getLdapServer(localStorage.token)) };
			})(),
			(async () => {
				oauthConfig = await getOAuthConfig(localStorage.token).catch(() => null);
			})()
		]);

		const ldapConfig = await getLdapConfig(localStorage.token);
		ENABLE_LDAP = ldapConfig.ENABLE_LDAP;
	});
</script>

<form class="flex h-full flex-col justify-between text-sm" on:submit|preventDefault={submitHandler}>
	<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-4">
		{$i18n.t('Authentication')}
	</h2>

	<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5">
		{#if adminConfig !== null}
			<AdminSettingSection title={$i18n.t('User Access')} first>
				<AdminSettingRow
					label={$i18n.t('Default User Role')}
					description={$i18n.t('Role assigned to new users when they create an account.')}
				>
					<SettingsSelect
						bind:value={adminConfig.DEFAULT_USER_ROLE}
						placeholder={$i18n.t('Select a role')}
					>
						<option value="pending">{$i18n.t('pending')}</option>
						<option value="user">{$i18n.t('user')}</option>
						<option value="admin">{$i18n.t('admin')}</option>
					</SettingsSelect>
				</AdminSettingRow>

				<AdminSettingRow
					label={$i18n.t('Default Group')}
					description={$i18n.t('Group assigned to new users by default.')}
				>
					<SettingsSelect
						bind:value={adminConfig.DEFAULT_GROUP_ID}
						placeholder={$i18n.t('Select a group')}
					>
						<option value={''}>None</option>
						{#each groups as group}
							<option value={group.id}>{group.name}</option>
						{/each}
					</SettingsSelect>
				</AdminSettingRow>

				<AdminSettingRow
					label={$i18n.t('New Sign Ups')}
					description={$i18n.t('Allow new users to create accounts.')}
				>
					<Switch bind:state={adminConfig.ENABLE_SIGNUP} />
				</AdminSettingRow>

				<AdminSettingRow
					label={$i18n.t('API Keys')}
					description={$i18n.t('Allow users to create API keys for programmatic access.')}
				>
					<Switch bind:state={adminConfig.ENABLE_API_KEYS} />
				</AdminSettingRow>

				{#if adminConfig?.ENABLE_API_KEYS}
					<AdminSettingRow
						label={$i18n.t('API Key Endpoint Restrictions')}
						description={$i18n.t('Limit API keys to configured endpoints.')}
					>
						<Switch bind:state={adminConfig.ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS} />
					</AdminSettingRow>

					{#if adminConfig?.ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS}
						<AdminSettingField
							label={$i18n.t('Allowed Endpoints')}
							description={$i18n.t('Comma-separated API paths that API keys can access.')}
						>
							<input
								class={inputClass}
								type="text"
								placeholder={`e.g.) /api/v1/messages, /api/v1/channels`}
								bind:value={adminConfig.API_KEYS_ALLOWED_ENDPOINTS}
							/>
							<a
								href="https://docs.openwebui.com/reference/api-endpoints"
								target="_blank"
								class="mt-1 block text-[0.6875rem] text-gray-400 underline hover:text-gray-700 dark:text-gray-600 dark:hover:text-gray-300"
							>
								{$i18n.t('To learn more about available endpoints, visit our documentation.')}
							</a>
						</AdminSettingField>
					{/if}
				{/if}

				<AdminSettingField
					label={$i18n.t('JWT Expiration')}
					description={$i18n.t(
						"Valid time units: 's', 'm', 'h', 'd', 'w' or '-1' for no expiration."
					)}
				>
					<input
						class={inputClass}
						type="text"
						placeholder={`e.g.) "30m","1h", "10d". `}
						bind:value={adminConfig.JWT_EXPIRES_IN}
					/>

					{#if adminConfig.JWT_EXPIRES_IN === '-1'}
						<a
							href="https://docs.openwebui.com/reference/env-configuration#jwt_expires_in"
							target="_blank"
							class="mt-1 block rounded-lg bg-yellow-500/10 px-2 py-1.5 text-[0.6875rem] text-yellow-700 underline dark:text-yellow-200"
						>
							{$i18n.t('No expiration can pose security risks.')}
						</a>
					{/if}
				</AdminSettingField>
			</AdminSettingSection>

			<AdminSettingSection title={$i18n.t('Pending Accounts')}>
				<AdminSettingRow
					label={$i18n.t('Admin Details')}
					description={$i18n.t('Show admin contact details while an account waits for approval.')}
				>
					<Switch bind:state={adminConfig.SHOW_ADMIN_DETAILS} />
				</AdminSettingRow>

				{#if adminConfig.SHOW_ADMIN_DETAILS}
					<AdminSettingField
						label={$i18n.t('Admin Contact Email')}
						description={$i18n.t('Email shown in the pending account overlay.')}
					>
						<input
							class={inputClass}
							type="email"
							placeholder={$i18n.t('Leave empty to use first admin user')}
							bind:value={adminConfig.ADMIN_EMAIL}
						/>
					</AdminSettingField>
				{/if}

				<AdminSettingField
					label={$i18n.t('Pending User Overlay Title')}
					description={$i18n.t('Custom title shown while an account waits for approval.')}
				>
					<Textarea
						className={textareaClass}
						placeholder={$i18n.t(
							'Enter a title for the pending user info overlay. Leave empty for default.'
						)}
						bind:value={adminConfig.PENDING_USER_OVERLAY_TITLE}
					/>
				</AdminSettingField>

				<AdminSettingField
					label={$i18n.t('Pending User Overlay Content')}
					description={$i18n.t('Custom message shown while an account waits for approval.')}
				>
					<Textarea
						className={textareaClass}
						placeholder={$i18n.t(
							'Enter content for the pending user info overlay. Leave empty for default.'
						)}
						bind:value={adminConfig.PENDING_USER_OVERLAY_CONTENT}
					/>
				</AdminSettingField>
			</AdminSettingSection>
		{/if}

		<AdminSettingSection title={$i18n.t('LDAP')}>
			<AdminSettingRow
				label={$i18n.t('LDAP')}
				description={$i18n.t('Allow users to authenticate with an LDAP directory.')}
			>
				<Switch bind:state={ENABLE_LDAP} />
			</AdminSettingRow>

			{#if ENABLE_LDAP}
				<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
					<AdminSettingField
						label={$i18n.t('Label')}
						description={$i18n.t('Display name for this LDAP connection.')}
					>
						<input
							class={inputClass}
							required
							placeholder={$i18n.t('Enter server label')}
							bind:value={LDAP_SERVER.label}
						/>
					</AdminSettingField>
				</div>

				<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
					<AdminSettingField
						label={$i18n.t('Host')}
						description={$i18n.t('LDAP server hostname or IP address.')}
					>
						<input
							class={inputClass}
							required
							placeholder={$i18n.t('Enter server host')}
							bind:value={LDAP_SERVER.host}
						/>
					</AdminSettingField>

					<AdminSettingField label={$i18n.t('Port')} description={$i18n.t('LDAP server port.')}>
						<Tooltip
							placement="top-start"
							content={$i18n.t('Default to 389 or 636 if TLS is enabled')}
							className="w-full"
						>
							<input
								class={inputClass}
								type="number"
								placeholder={$i18n.t('Enter server port')}
								bind:value={LDAP_SERVER.port}
							/>
						</Tooltip>
					</AdminSettingField>
				</div>

				<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
					<AdminSettingField
						label={$i18n.t('Application DN')}
						description={$i18n.t('Bind DN used for directory search.')}
					>
						<Tooltip
							content={$i18n.t('The Application Account DN you bind with for search')}
							placement="top-start"
						>
							<input
								class={inputClass}
								placeholder={$i18n.t('Enter Application DN')}
								bind:value={LDAP_SERVER.app_dn}
							/>
						</Tooltip>
					</AdminSettingField>

					<AdminSettingField
						label={$i18n.t('Application DN Password')}
						description={$i18n.t('Password for the bind DN.')}
					>
						<SensitiveInput
							variant="settings"
							placeholder={$i18n.t('Enter Application DN Password')}
							required={false}
							bind:value={LDAP_SERVER.app_dn_password}
						/>
					</AdminSettingField>
				</div>

				<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
					<AdminSettingField
						label={$i18n.t('Attribute for Mail')}
						description={$i18n.t('LDAP attribute used as the user email address.')}
					>
						<Tooltip
							content={$i18n.t(
								'The LDAP attribute that maps to the mail that users use to sign in.'
							)}
							placement="top-start"
						>
							<input
								class={inputClass}
								required
								placeholder={$i18n.t('Example: mail')}
								bind:value={LDAP_SERVER.attribute_for_mail}
							/>
						</Tooltip>
					</AdminSettingField>

					<AdminSettingField
						label={$i18n.t('Attribute for Username')}
						description={$i18n.t('LDAP attribute used as the username.')}
					>
						<Tooltip
							content={$i18n.t(
								'The LDAP attribute that maps to the username that users use to sign in.'
							)}
							placement="top-start"
						>
							<input
								class={inputClass}
								required
								placeholder={$i18n.t('Example: sAMAccountName or uid or userPrincipalName')}
								bind:value={LDAP_SERVER.attribute_for_username}
							/>
						</Tooltip>
					</AdminSettingField>
				</div>

				<AdminSettingField
					label={$i18n.t('Search Base')}
					description={$i18n.t('Base DN used when searching for users.')}
				>
					<Tooltip content={$i18n.t('The base to search for users')} placement="top-start">
						<input
							class={inputClass}
							required
							placeholder={$i18n.t('Example: ou=users,dc=foo,dc=example')}
							bind:value={LDAP_SERVER.search_base}
						/>
					</Tooltip>
				</AdminSettingField>

				<AdminSettingField
					label={$i18n.t('Search Filters')}
					description={$i18n.t('LDAP filter used to match signing-in users.')}
				>
					<input
						class={inputClass}
						placeholder={$i18n.t('Example: (&(objectClass=inetOrgPerson)(uid=%s))')}
						bind:value={LDAP_SERVER.search_filters}
					/>
					<a
						class="mt-1 block text-[0.6875rem] text-gray-400 underline hover:text-gray-700 dark:text-gray-600 dark:hover:text-gray-300"
						href="https://ldap.com/ldap-filters/"
						target="_blank"
					>
						{$i18n.t('Click here for filter guides.')}
					</a>
				</AdminSettingField>

				<AdminSettingRow
					label={$i18n.t('TLS')}
					description={$i18n.t('Use TLS when connecting to the LDAP server.')}
				>
					<Switch bind:state={LDAP_SERVER.use_tls} />
				</AdminSettingRow>

				{#if LDAP_SERVER.use_tls}
					<AdminSettingField
						label={$i18n.t('Certificate Path')}
						description={$i18n.t('Certificate file used for TLS verification.')}
					>
						<input
							class={inputClass}
							placeholder={$i18n.t('Enter certificate path')}
							bind:value={LDAP_SERVER.certificate_path}
						/>
					</AdminSettingField>

					<AdminSettingRow
						label={$i18n.t('Validate Certificate')}
						description={$i18n.t('Verify the LDAP server certificate when TLS is enabled.')}
					>
						<Switch bind:state={LDAP_SERVER.validate_cert} />
					</AdminSettingRow>

					<AdminSettingField
						label={$i18n.t('Ciphers')}
						description={$i18n.t('TLS cipher list for LDAP connections.')}
					>
						<Tooltip content={$i18n.t('Default to ALL')} placement="top-start">
							<input
								class={inputClass}
								placeholder={$i18n.t('Example: ALL')}
								bind:value={LDAP_SERVER.ciphers}
							/>
						</Tooltip>
					</AdminSettingField>
				{/if}

				<AdminSettingRow
					label={$i18n.t('Group Mapping')}
					description={$i18n.t('Map LDAP groups to Open WebUI groups.')}
				>
					<Switch bind:state={LDAP_SERVER.enable_group_management} />
				</AdminSettingRow>

				{#if LDAP_SERVER.enable_group_management}
					<AdminSettingRow
						label={$i18n.t('Auto-Create Groups')}
						description={$i18n.t('Create missing groups from LDAP groups.')}
					>
						<Switch bind:state={LDAP_SERVER.enable_group_creation} />
					</AdminSettingRow>

					<AdminSettingField
						label={$i18n.t('Group Attribute')}
						description={$i18n.t('LDAP attribute containing the user group memberships.')}
					>
						<Tooltip content={$i18n.t('Default to memberOf')} placement="top-start">
							<input
								class={inputClass}
								placeholder="memberOf"
								bind:value={LDAP_SERVER.attribute_for_groups}
							/>
						</Tooltip>
					</AdminSettingField>
				{/if}
			{/if}
		</AdminSettingSection>

		{#if oauthConfig}
			<AdminSettingSection title={$i18n.t('OAuth / OIDC')}>
				<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
					<AdminSettingField
						label={$i18n.t('Provider Name')}
						description={$i18n.t('Display name shown for the OAuth provider.')}
					>
						<input
							class={inputClass}
							placeholder="SSO"
							bind:value={oauthConfig.OAUTH_PROVIDER_NAME}
						/>
					</AdminSettingField>

					<AdminSettingField
						label={$i18n.t('Provider URL')}
						description={$i18n.t('OpenID discovery URL for this provider.')}
					>
						<input
							class={inputClass}
							placeholder="https://accounts.google.com/.well-known/openid-configuration"
							bind:value={oauthConfig.OPENID_PROVIDER_URL}
						/>
					</AdminSettingField>
				</div>

				<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
					<AdminSettingField
						label={$i18n.t('Client ID')}
						description={$i18n.t('OAuth client identifier from the provider.')}
					>
						<input
							class={inputClass}
							placeholder={$i18n.t('Enter Client ID')}
							bind:value={oauthConfig.OAUTH_CLIENT_ID}
						/>
					</AdminSettingField>

					<AdminSettingField
						label={$i18n.t('Client Secret')}
						description={$i18n.t('OAuth client secret from the provider.')}
					>
						<SensitiveInput
							variant="settings"
							placeholder={$i18n.t('Enter Client Secret')}
							required={false}
							bind:value={oauthConfig.OAUTH_CLIENT_SECRET}
						/>
					</AdminSettingField>
				</div>

				<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
					<AdminSettingField
						label={$i18n.t('Redirect URI')}
						description={$i18n.t('Callback URI registered with the provider.')}
					>
						<input
							class={inputClass}
							placeholder={$i18n.t('Enter Redirect URI')}
							bind:value={oauthConfig.OPENID_REDIRECT_URI}
						/>
					</AdminSettingField>

					<AdminSettingField
						label={$i18n.t('Scopes')}
						description={$i18n.t('OAuth scopes requested during sign-in.')}
					>
						<input
							class={inputClass}
							placeholder="openid email profile"
							bind:value={oauthConfig.OAUTH_SCOPES}
						/>
					</AdminSettingField>
				</div>

				<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
					<AdminSettingField
						label={$i18n.t('Email Claim')}
						description={$i18n.t('Claim used as the user email address.')}
					>
						<input
							class={inputClass}
							placeholder="email"
							bind:value={oauthConfig.OAUTH_EMAIL_CLAIM}
						/>
					</AdminSettingField>

					<AdminSettingField
						label={$i18n.t('Username Claim')}
						description={$i18n.t('Claim used as the display name.')}
					>
						<input
							class={inputClass}
							placeholder="name"
							bind:value={oauthConfig.OAUTH_USERNAME_CLAIM}
						/>
					</AdminSettingField>
				</div>

				<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
					<AdminSettingField
						label={$i18n.t('Picture Claim')}
						description={$i18n.t('Claim used as the profile picture URL.')}
					>
						<input
							class={inputClass}
							placeholder="picture"
							bind:value={oauthConfig.OAUTH_PICTURE_CLAIM}
						/>
					</AdminSettingField>

					<AdminSettingField
						label={$i18n.t('Sub Claim')}
						description={$i18n.t('Claim used as the stable user identifier.')}
					>
						<input class={inputClass} placeholder="sub" bind:value={oauthConfig.OAUTH_SUB_CLAIM} />
					</AdminSettingField>
				</div>

				<AdminSettingRow
					label={$i18n.t('OAuth Signup')}
					description={$i18n.t('Allow users to create accounts through OAuth.')}
				>
					<Switch bind:state={oauthConfig.ENABLE_OAUTH_SIGNUP} />
				</AdminSettingRow>

				<AdminSettingRow
					label={$i18n.t('Merge Accounts by Email')}
					description={$i18n.t('Link OAuth sign-ins to existing accounts with the same email.')}
				>
					<Switch bind:state={oauthConfig.OAUTH_MERGE_ACCOUNTS_BY_EMAIL} />
				</AdminSettingRow>

				<AdminSettingRow
					label={$i18n.t('Auto Redirect')}
					description={$i18n.t('Send users directly to the OAuth provider from the sign-in page.')}
				>
					<Switch bind:state={oauthConfig.OAUTH_AUTO_REDIRECT} />
				</AdminSettingRow>

				<AdminSettingField
					label={$i18n.t('Allowed Domains')}
					description={$i18n.t('Email domains allowed to sign in with OAuth.')}
				>
					<input
						class={inputClass}
						placeholder="* (all domains)"
						bind:value={oauthConfig.OAUTH_ALLOWED_DOMAINS}
					/>
				</AdminSettingField>

				<AdminSettingRow
					label={$i18n.t('Role Mapping')}
					description={$i18n.t('Map OAuth claims to Open WebUI roles.')}
				>
					<Switch bind:state={oauthConfig.ENABLE_OAUTH_ROLE_MANAGEMENT} />
				</AdminSettingRow>

				{#if oauthConfig.ENABLE_OAUTH_ROLE_MANAGEMENT}
					<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
						<AdminSettingField
							label={$i18n.t('Roles Claim')}
							description={$i18n.t('Claim containing provider roles.')}
						>
							<input
								class={inputClass}
								placeholder="roles"
								bind:value={oauthConfig.OAUTH_ROLES_CLAIM}
							/>
						</AdminSettingField>

						<AdminSettingField
							label={$i18n.t('Admin Roles')}
							description={$i18n.t('Provider roles that grant admin access.')}
						>
							<input
								class={inputClass}
								placeholder="admin"
								bind:value={oauthConfig.OAUTH_ADMIN_ROLES}
							/>
						</AdminSettingField>
					</div>

					<AdminSettingField
						label={$i18n.t('Allowed Roles')}
						description={$i18n.t('Provider roles allowed to sign in.')}
					>
						<input
							class={inputClass}
							placeholder="*"
							bind:value={oauthConfig.OAUTH_ALLOWED_ROLES}
						/>
					</AdminSettingField>
				{/if}

				<AdminSettingRow
					label={$i18n.t('Group Mapping')}
					description={$i18n.t('Map OAuth claims to Open WebUI groups.')}
				>
					<Switch bind:state={oauthConfig.ENABLE_OAUTH_GROUP_MANAGEMENT} />
				</AdminSettingRow>

				{#if oauthConfig.ENABLE_OAUTH_GROUP_MANAGEMENT}
					<AdminSettingRow
						label={$i18n.t('Auto-Create Groups')}
						description={$i18n.t('Create missing groups from OAuth claims.')}
					>
						<Switch bind:state={oauthConfig.ENABLE_OAUTH_GROUP_CREATION} />
					</AdminSettingRow>

					<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
						<AdminSettingField
							label={$i18n.t('Group Claim')}
							description={$i18n.t('Claim containing provider groups.')}
						>
							<input
								class={inputClass}
								placeholder="groups"
								bind:value={oauthConfig.OAUTH_GROUP_CLAIM}
							/>
						</AdminSettingField>

						<AdminSettingField
							label={$i18n.t('Blocked Groups')}
							description={$i18n.t('Provider groups blocked from signing in.')}
						>
							<input
								class={inputClass}
								placeholder={$i18n.t('Comma-separated group names')}
								bind:value={oauthConfig.OAUTH_BLOCKED_GROUPS}
							/>
						</AdminSettingField>
					</div>
				{/if}

				<AdminSettingRow
					label={$i18n.t('Update Email')}
					description={$i18n.t('Refresh the account email from OAuth on sign-in.')}
				>
					<Switch bind:state={oauthConfig.OAUTH_UPDATE_EMAIL_ON_LOGIN} />
				</AdminSettingRow>

				<AdminSettingRow
					label={$i18n.t('Update Name')}
					description={$i18n.t('Refresh the account name from OAuth on sign-in.')}
				>
					<Switch bind:state={oauthConfig.OAUTH_UPDATE_NAME_ON_LOGIN} />
				</AdminSettingRow>

				<AdminSettingRow
					label={$i18n.t('Update Picture')}
					description={$i18n.t('Refresh the profile picture from OAuth on sign-in.')}
				>
					<Switch bind:state={oauthConfig.OAUTH_UPDATE_PICTURE_ON_LOGIN} />
				</AdminSettingRow>
			</AdminSettingSection>
		{/if}
	</div>

	<div class="flex justify-end pt-6 text-sm font-normal">
		<button
			class="px-3.5 py-1.5 text-sm font-normal bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
