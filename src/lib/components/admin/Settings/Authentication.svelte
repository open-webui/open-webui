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
		port: null,
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
	$: oauthEditable = oauthConfig?.ENABLE_OAUTH_PERSISTENT_CONFIG ?? true;
	const inputClass =
		'w-full h-7 rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';
	const textareaClass =
		'w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';

	const updateLdapServerHandler = async () => {
		await updateLdapConfig(localStorage.token, ENABLE_LDAP);
		if (!ENABLE_LDAP) return true;

		// Honor the "Default to memberOf" hint: fall back to the default group
		// attribute when it is left blank while group management is enabled, so
		// the save isn't rejected by the backend's required-field check.
		if (LDAP_SERVER.enable_group_management && !LDAP_SERVER.attribute_for_groups?.trim()) {
			LDAP_SERVER.attribute_for_groups = 'memberOf';
		}

		const res = await updateLdapServer(localStorage.token, LDAP_SERVER).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		return !!res;
	};

	const updateOAuthHandler = async () => {
		if (!oauthConfig || !oauthEditable) return true;
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
		if (res) {
			adminConfig = res;
		}
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
		{$i18n.t('settings.admin.authentication.title')}
	</h2>

	<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5">
		{#if adminConfig !== null}
			<AdminSettingSection
				title={$i18n.t('settings.admin.authentication.sections.userAccess.title')}
				first
			>
				<AdminSettingRow
					label={$i18n.t('settings.admin.authentication.defaultUserRole.label')}
					description={$i18n.t('settings.admin.authentication.defaultUserRole.description')}
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
					label={$i18n.t('settings.admin.authentication.defaultGroup.label')}
					description={$i18n.t('settings.admin.authentication.defaultGroup.description')}
				>
					<SettingsSelect
						bind:value={adminConfig.DEFAULT_GROUP_ID}
						placeholder={$i18n.t('Select a group')}
					>
						<option value={''}>{$i18n.t('None')}</option>
						{#each groups as group}
							<option value={group.id}>{group.name}</option>
						{/each}
					</SettingsSelect>
				</AdminSettingRow>

				<AdminSettingRow
					label={$i18n.t('settings.admin.authentication.loginForm.label')}
					description={$i18n.t('settings.admin.authentication.loginForm.description')}
					let:labelId
				>
					<Switch bind:state={adminConfig.ENABLE_LOGIN_FORM} ariaLabelledbyId={labelId} />
				</AdminSettingRow>

				<AdminSettingRow
					label={$i18n.t('settings.admin.authentication.newSignUps.label')}
					description={$i18n.t('settings.admin.authentication.newSignUps.description')}
					let:labelId
				>
					<Switch bind:state={adminConfig.ENABLE_SIGNUP} ariaLabelledbyId={labelId} />
				</AdminSettingRow>

				<AdminSettingRow
					label={$i18n.t('settings.admin.authentication.apiKeys.label')}
					description={$i18n.t('settings.admin.authentication.apiKeys.description')}
					let:labelId
				>
					<Switch bind:state={adminConfig.ENABLE_API_KEYS} ariaLabelledbyId={labelId} />
				</AdminSettingRow>

				{#if adminConfig?.ENABLE_API_KEYS}
					<AdminSettingRow
						label={$i18n.t('settings.admin.authentication.apiKeyEndpointRestrictions.label')}
						description={$i18n.t(
							'settings.admin.authentication.apiKeyEndpointRestrictions.description'
						)}
						let:labelId
					>
						<Switch
							bind:state={adminConfig.ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS}
							ariaLabelledbyId={labelId}
						/>
					</AdminSettingRow>

					{#if adminConfig?.ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS}
						<AdminSettingField
							label={$i18n.t('settings.admin.authentication.allowedEndpoints.label')}
							description={$i18n.t('settings.admin.authentication.allowedEndpoints.description')}
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
					label={$i18n.t('settings.admin.authentication.jwtExpiration.label')}
					description={$i18n.t('settings.admin.authentication.jwtExpiration.description')}
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

			<AdminSettingSection
				title={$i18n.t('settings.admin.authentication.sections.pendingAccounts.title')}
			>
				<AdminSettingRow
					label={$i18n.t('settings.admin.authentication.adminDetails.label')}
					description={$i18n.t('settings.admin.authentication.adminDetails.description')}
					let:labelId
				>
					<Switch bind:state={adminConfig.SHOW_ADMIN_DETAILS} ariaLabelledbyId={labelId} />
				</AdminSettingRow>

				{#if adminConfig.SHOW_ADMIN_DETAILS}
					<AdminSettingField
						label={$i18n.t('settings.admin.authentication.adminContactEmail.label')}
						description={$i18n.t('settings.admin.authentication.adminContactEmail.description')}
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
					label={$i18n.t('settings.admin.authentication.pendingUserOverlayTitle.label')}
					description={$i18n.t('settings.admin.authentication.pendingUserOverlayTitle.description')}
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
					label={$i18n.t('settings.admin.authentication.pendingUserOverlayContent.label')}
					description={$i18n.t(
						'settings.admin.authentication.pendingUserOverlayContent.description'
					)}
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

		<AdminSettingSection title={$i18n.t('settings.admin.authentication.sections.ldap.title')}>
			<AdminSettingRow
				label={$i18n.t('settings.admin.authentication.ldap.label')}
				description={$i18n.t('settings.admin.authentication.ldap.description')}
				let:labelId
			>
				<Switch bind:state={ENABLE_LDAP} ariaLabelledbyId={labelId} />
			</AdminSettingRow>

			{#if ENABLE_LDAP}
				<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
					<AdminSettingField
						label={$i18n.t('settings.admin.authentication.label.label')}
						description={$i18n.t('settings.admin.authentication.label.description')}
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
						label={$i18n.t('settings.admin.authentication.host.label')}
						description={$i18n.t('settings.admin.authentication.host.description')}
					>
						<input
							class={inputClass}
							required
							placeholder={$i18n.t('Enter server host')}
							bind:value={LDAP_SERVER.host}
						/>
					</AdminSettingField>

					<AdminSettingField
						label={$i18n.t('settings.admin.authentication.port.label')}
						description={$i18n.t('settings.admin.authentication.port.description')}
					>
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
						label={$i18n.t('settings.admin.authentication.applicationDn.label')}
						description={$i18n.t('settings.admin.authentication.applicationDn.description')}
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
						label={$i18n.t('settings.admin.authentication.applicationDnPassword.label')}
						description={$i18n.t('settings.admin.authentication.applicationDnPassword.description')}
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
						label={$i18n.t('settings.admin.authentication.attributeForMail.label')}
						description={$i18n.t('settings.admin.authentication.attributeForMail.description')}
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
						label={$i18n.t('settings.admin.authentication.attributeForUsername.label')}
						description={$i18n.t('settings.admin.authentication.attributeForUsername.description')}
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
					label={$i18n.t('settings.admin.authentication.searchBase.label')}
					description={$i18n.t('settings.admin.authentication.searchBase.description')}
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
					label={$i18n.t('settings.admin.authentication.searchFilters.label')}
					description={$i18n.t('settings.admin.authentication.searchFilters.description')}
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
					label={$i18n.t('settings.admin.authentication.tls.label')}
					description={$i18n.t('settings.admin.authentication.tls.description')}
					let:labelId
				>
					<Switch bind:state={LDAP_SERVER.use_tls} ariaLabelledbyId={labelId} />
				</AdminSettingRow>

				{#if LDAP_SERVER.use_tls}
					<AdminSettingField
						label={$i18n.t('settings.admin.authentication.certificatePath.label')}
						description={$i18n.t('settings.admin.authentication.certificatePath.description')}
					>
						<input
							class={inputClass}
							placeholder={$i18n.t('Enter certificate path')}
							bind:value={LDAP_SERVER.certificate_path}
						/>
					</AdminSettingField>

					<AdminSettingRow
						label={$i18n.t('settings.admin.authentication.validateCertificate.label')}
						description={$i18n.t('settings.admin.authentication.validateCertificate.description')}
						let:labelId
					>
						<Switch bind:state={LDAP_SERVER.validate_cert} ariaLabelledbyId={labelId} />
					</AdminSettingRow>

					<AdminSettingField
						label={$i18n.t('settings.admin.authentication.ciphers.label')}
						description={$i18n.t('settings.admin.authentication.ciphers.description')}
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

				<!-- LICENSE covers this Open WebUI wordmark.
					Do not alter, remove, obscure, or replace it except as LICENSE permits:
					https://docs.openwebui.com/license. -->
				<AdminSettingRow
					label={$i18n.t('settings.admin.authentication.enableGroupManagement.label')}
					description={$i18n.t('settings.admin.authentication.enableGroupManagement.description')}
					let:labelId
				>
					<Switch bind:state={LDAP_SERVER.enable_group_management} ariaLabelledbyId={labelId} />
				</AdminSettingRow>

				{#if LDAP_SERVER.enable_group_management}
					<AdminSettingRow
						label={$i18n.t('settings.admin.authentication.enableGroupCreation.label')}
						description={$i18n.t('settings.admin.authentication.enableGroupCreation.description')}
						let:labelId
					>
						<Switch bind:state={LDAP_SERVER.enable_group_creation} ariaLabelledbyId={labelId} />
					</AdminSettingRow>

					<AdminSettingField
						label={$i18n.t('settings.admin.authentication.groupAttribute.label')}
						description={$i18n.t('settings.admin.authentication.groupAttribute.description')}
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
			<AdminSettingSection
				title={$i18n.t('settings.admin.authentication.sections.oauthOidc.title')}
			>
				{#if !oauthEditable}
					<div
						class="rounded-lg bg-yellow-500/10 px-2 py-1.5 text-[0.6875rem] text-yellow-700 dark:text-yellow-200"
					>
						{$i18n.t(
							'These settings are read from environment variables and cannot be edited here while {{ENV_VAR}} is disabled.',
							{ ENV_VAR: 'ENABLE_OAUTH_PERSISTENT_CONFIG' }
						)}
					</div>
				{/if}

				<fieldset
					class="flex min-w-0 flex-col gap-2.5 disabled:cursor-not-allowed disabled:opacity-75"
					disabled={!oauthEditable}
				>
					<AdminSettingRow
						label={$i18n.t('settings.admin.authentication.oauthOidc.label')}
						description={$i18n.t('settings.admin.authentication.oauthOidc.description')}
						let:labelId
					>
						<Switch bind:state={oauthConfig.ENABLE_OAUTH} ariaLabelledbyId={labelId} />
					</AdminSettingRow>

					{#if oauthConfig.ENABLE_OAUTH}
						<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
							<AdminSettingField
								label={$i18n.t('settings.admin.authentication.providerName.label')}
								description={$i18n.t('settings.admin.authentication.providerName.description')}
							>
								<input
									class={inputClass}
									placeholder="SSO"
									bind:value={oauthConfig.OAUTH_PROVIDER_NAME}
								/>
							</AdminSettingField>

							<AdminSettingField
								label={$i18n.t('settings.admin.authentication.providerUrl.label')}
								description={$i18n.t('settings.admin.authentication.providerUrl.description')}
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
								label={$i18n.t('settings.admin.authentication.clientId.label')}
								description={$i18n.t('settings.admin.authentication.clientId.description')}
							>
								<input
									class={inputClass}
									placeholder={$i18n.t('Enter Client ID')}
									bind:value={oauthConfig.OAUTH_CLIENT_ID}
								/>
							</AdminSettingField>

							<AdminSettingField
								label={$i18n.t('settings.admin.authentication.clientSecret.label')}
								description={$i18n.t('settings.admin.authentication.clientSecret.description')}
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
								label={$i18n.t('settings.admin.authentication.redirectUri.label')}
								description={$i18n.t('settings.admin.authentication.redirectUri.description')}
							>
								<input
									class={inputClass}
									placeholder={$i18n.t('Enter Redirect URI')}
									bind:value={oauthConfig.OPENID_REDIRECT_URI}
								/>
							</AdminSettingField>

							<AdminSettingField
								label={$i18n.t('settings.admin.authentication.scopes.label')}
								description={$i18n.t('settings.admin.authentication.scopes.description')}
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
								label={$i18n.t('settings.admin.authentication.emailClaim.label')}
								description={$i18n.t('settings.admin.authentication.emailClaim.description')}
							>
								<input
									class={inputClass}
									placeholder="email"
									bind:value={oauthConfig.OAUTH_EMAIL_CLAIM}
								/>
							</AdminSettingField>

							<AdminSettingField
								label={$i18n.t('settings.admin.authentication.usernameClaim.label')}
								description={$i18n.t('settings.admin.authentication.usernameClaim.description')}
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
								label={$i18n.t('settings.admin.authentication.pictureClaim.label')}
								description={$i18n.t('settings.admin.authentication.pictureClaim.description')}
							>
								<input
									class={inputClass}
									placeholder="picture"
									bind:value={oauthConfig.OAUTH_PICTURE_CLAIM}
								/>
							</AdminSettingField>

							<AdminSettingField
								label={$i18n.t('settings.admin.authentication.subClaim.label')}
								description={$i18n.t('settings.admin.authentication.subClaim.description')}
							>
								<input
									class={inputClass}
									placeholder="sub"
									bind:value={oauthConfig.OAUTH_SUB_CLAIM}
								/>
							</AdminSettingField>
						</div>

						<AdminSettingRow
							label={$i18n.t('settings.admin.authentication.oauthSignup.label')}
							description={$i18n.t('settings.admin.authentication.oauthSignup.description')}
							let:labelId
						>
							<Switch bind:state={oauthConfig.ENABLE_OAUTH_SIGNUP} ariaLabelledbyId={labelId} />
						</AdminSettingRow>

						<AdminSettingRow
							label={$i18n.t('settings.admin.authentication.mergeAccountsByEmail.label')}
							description={$i18n.t(
								'settings.admin.authentication.mergeAccountsByEmail.description'
							)}
							let:labelId
						>
							<Switch
								bind:state={oauthConfig.OAUTH_MERGE_ACCOUNTS_BY_EMAIL}
								ariaLabelledbyId={labelId}
							/>
						</AdminSettingRow>

						<AdminSettingRow
							label={$i18n.t('settings.admin.authentication.autoRedirect.label')}
							description={$i18n.t('settings.admin.authentication.autoRedirect.description')}
							let:labelId
						>
							<Switch bind:state={oauthConfig.OAUTH_AUTO_REDIRECT} ariaLabelledbyId={labelId} />
						</AdminSettingRow>

						<AdminSettingField
							label={$i18n.t('settings.admin.authentication.allowedDomains.label')}
							description={$i18n.t('settings.admin.authentication.allowedDomains.description')}
						>
							<input
								class={inputClass}
								placeholder={$i18n.t('* (all domains)')}
								bind:value={oauthConfig.OAUTH_ALLOWED_DOMAINS}
							/>
						</AdminSettingField>

						<!-- LICENSE covers this Open WebUI wordmark.
						Do not alter, remove, obscure, or replace it except as LICENSE permits:
						https://docs.openwebui.com/license. -->
						<AdminSettingRow
							label={$i18n.t('settings.admin.authentication.roleMapping.label')}
							description={$i18n.t('settings.admin.authentication.roleMapping.description')}
							let:labelId
						>
							<Switch
								bind:state={oauthConfig.ENABLE_OAUTH_ROLE_MANAGEMENT}
								ariaLabelledbyId={labelId}
							/>
						</AdminSettingRow>

						{#if oauthConfig.ENABLE_OAUTH_ROLE_MANAGEMENT}
							<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
								<AdminSettingField
									label={$i18n.t('settings.admin.authentication.rolesClaim.label')}
									description={$i18n.t('settings.admin.authentication.rolesClaim.description')}
								>
									<input
										class={inputClass}
										placeholder="roles"
										bind:value={oauthConfig.OAUTH_ROLES_CLAIM}
									/>
								</AdminSettingField>

								<AdminSettingField
									label={$i18n.t('settings.admin.authentication.adminRoles.label')}
									description={$i18n.t('settings.admin.authentication.adminRoles.description')}
								>
									<input
										class={inputClass}
										placeholder="admin"
										bind:value={oauthConfig.OAUTH_ADMIN_ROLES}
									/>
								</AdminSettingField>
							</div>

							<AdminSettingField
								label={$i18n.t('settings.admin.authentication.allowedRoles.label')}
								description={$i18n.t('settings.admin.authentication.allowedRoles.description')}
							>
								<input
									class={inputClass}
									placeholder="*"
									bind:value={oauthConfig.OAUTH_ALLOWED_ROLES}
								/>
							</AdminSettingField>
						{/if}

						<!-- LICENSE covers this Open WebUI wordmark.
						Do not alter, remove, obscure, or replace it except as LICENSE permits:
						https://docs.openwebui.com/license. -->
						<AdminSettingRow
							label={$i18n.t('settings.admin.authentication.enableOauthGroupManagement.label')}
							description={$i18n.t(
								'settings.admin.authentication.enableOauthGroupManagement.description'
							)}
							let:labelId
						>
							<Switch
								bind:state={oauthConfig.ENABLE_OAUTH_GROUP_MANAGEMENT}
								ariaLabelledbyId={labelId}
							/>
						</AdminSettingRow>

						{#if oauthConfig.ENABLE_OAUTH_GROUP_MANAGEMENT}
							<AdminSettingRow
								label={$i18n.t('settings.admin.authentication.enableOauthGroupCreation.label')}
								description={$i18n.t(
									'settings.admin.authentication.enableOauthGroupCreation.description'
								)}
								let:labelId
							>
								<Switch
									bind:state={oauthConfig.ENABLE_OAUTH_GROUP_CREATION}
									ariaLabelledbyId={labelId}
								/>
							</AdminSettingRow>

							<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
								<AdminSettingField
									label={$i18n.t('settings.admin.authentication.groupClaim.label')}
									description={$i18n.t('settings.admin.authentication.groupClaim.description')}
								>
									<input
										class={inputClass}
										placeholder="groups"
										bind:value={oauthConfig.OAUTH_GROUP_CLAIM}
									/>
								</AdminSettingField>

								<AdminSettingField
									label={$i18n.t('settings.admin.authentication.blockedGroups.label')}
									description={$i18n.t('settings.admin.authentication.blockedGroups.description')}
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
							label={$i18n.t('settings.admin.authentication.updateEmail.label')}
							description={$i18n.t('settings.admin.authentication.updateEmail.description')}
							let:labelId
						>
							<Switch
								bind:state={oauthConfig.OAUTH_UPDATE_EMAIL_ON_LOGIN}
								ariaLabelledbyId={labelId}
							/>
						</AdminSettingRow>

						<AdminSettingRow
							label={$i18n.t('settings.admin.authentication.updateName.label')}
							description={$i18n.t('settings.admin.authentication.updateName.description')}
							let:labelId
						>
							<Switch
								bind:state={oauthConfig.OAUTH_UPDATE_NAME_ON_LOGIN}
								ariaLabelledbyId={labelId}
							/>
						</AdminSettingRow>

						<AdminSettingRow
							label={$i18n.t('settings.admin.authentication.updatePicture.label')}
							description={$i18n.t('settings.admin.authentication.updatePicture.description')}
							let:labelId
						>
							<Switch
								bind:state={oauthConfig.OAUTH_UPDATE_PICTURE_ON_LOGIN}
								ariaLabelledbyId={labelId}
							/>
						</AdminSettingRow>
					{/if}
				</fieldset>
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
