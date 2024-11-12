<script lang="ts">
	import { getBackendConfig, getModelFilterConfig, updateModelFilterConfig } from '$lib/apis';
	import { getSignUpEnabledStatus, toggleSignUpEnabledStatus } from '$lib/apis/auths';
	import { getUserPermissions, updateUserPermissions } from '$lib/apis/users';

	import {
		getLdapConfig,
		updateLdapConfig,
		getLdapServer,
		updateLdapServer
	} from '$lib/apis/auths';

	import { onMount, getContext } from 'svelte';
	import { models, config } from '$lib/stores';
	import Switch from '$lib/components/common/Switch.svelte';
	import { setDefaultModels } from '$lib/apis/configs';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let defaultModelId = '';

	let whitelistEnabled = false;
	let whitelistModels = [''];
	let permissions = {
		chat: {
			deletion: true,
			edit: true,
			temporary: true
		}
	};

	let chatDeletion = true;
	let chatEdit = true;
	let chatTemporary = true;

	// LDAP
	let ENABLE_LDAP = false;
	let LDAP_SERVER = {
		label: '',
		host: '',
		port: '',
		attribute_for_username: 'uid',
		app_dn: '',
		app_dn_password: '',
		search_base: '',
		search_filters: '',
		use_tls: false,
		certificate_path: '',
		ciphers: ''
	};

	const updateLdapServerHandler = async () => {
		if (!ENABLE_LDAP) return;
		const res = await updateLdapServer(localStorage.token, LDAP_SERVER).catch((error) => {
			toast.error(error);
			return null;
		});
		if (res) {
			toast.success($i18n.t('LDAP server updated'));
		}
	};

	onMount(async () => {
		permissions = await getUserPermissions(localStorage.token);

		chatDeletion = permissions?.chat?.deletion ?? true;
		chatEdit = permissions?.chat?.editing ?? true;
		chatTemporary = permissions?.chat?.temporary ?? true;

		const res = await getModelFilterConfig(localStorage.token);
		if (res) {
			whitelistEnabled = res.enabled;
			whitelistModels = res.models.length > 0 ? res.models : [''];
		}

		(async () => {
			LDAP_SERVER = await getLdapServer(localStorage.token);
		})();

		const ldapConfig = await getLdapConfig(localStorage.token);
		ENABLE_LDAP = ldapConfig.ENABLE_LDAP;

		defaultModelId = $config.default_models ? $config?.default_models.split(',')[0] : '';
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={async () => {
		// console.log('submit');

		await setDefaultModels(localStorage.token, defaultModelId);
		await updateUserPermissions(localStorage.token, {
			chat: {
				deletion: chatDeletion,
				editing: chatEdit,
				temporary: chatTemporary
			}
		});
		await updateModelFilterConfig(localStorage.token, whitelistEnabled, whitelistModels);

		await updateLdapServerHandler();

		saveHandler();

		await config.set(await getBackendConfig());
	}}
>
	<div class=" space-y-3 overflow-y-scroll max-h-full pr-1.5">
		<div>
			<div class=" mb-2 text-sm font-medium">{$i18n.t('User Permissions')}</div>

			<div class="  flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">{$i18n.t('Allow Chat Deletion')}</div>

				<Switch bind:state={chatDeletion} />
			</div>

			<div class="  flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">{$i18n.t('Allow Chat Editing')}</div>

				<Switch bind:state={chatEdit} />
			</div>

			<div class="  flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">{$i18n.t('Allow Temporary Chat')}</div>

				<Switch bind:state={chatTemporary} />
			</div>
		</div>

		<hr class=" border-gray-50 dark:border-gray-850" />

		<div class=" space-y-3">
			<div class="mt-2 space-y-2 pr-1.5">
				<div class="flex justify-between items-center text-sm">
					<div class="  font-medium">{$i18n.t('LDAP')}</div>

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
					<div class="flex flex-col gap-1">
						<div class="flex w-full gap-2">
							<div class="w-full">
								<div class=" self-center text-xs font-medium min-w-fit mb-1">
									{$i18n.t('Label')}
								</div>
								<input
									class="w-full bg-transparent outline-none py-0.5"
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
									class="w-full bg-transparent outline-none py-0.5"
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
										class="w-full bg-transparent outline-none py-0.5"
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
										class="w-full bg-transparent outline-none py-0.5"
										required
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
									bind:value={LDAP_SERVER.app_dn_password}
								/>
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
										class="w-full bg-transparent outline-none py-0.5"
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
										class="w-full bg-transparent outline-none py-0.5"
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
									class="w-full bg-transparent outline-none py-0.5"
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
											class="w-full bg-transparent outline-none py-0.5"
											required
											placeholder={$i18n.t('Enter certificate path')}
											bind:value={LDAP_SERVER.certificate_path}
										/>
									</div>
								</div>
								<div class="flex w-full gap-2">
									<div class="w-full">
										<div class=" self-center text-xs font-medium min-w-fit mb-1">
											{$i18n.t('Ciphers')}
										</div>
										<Tooltip content={$i18n.t('Default to ALL')} placement="top-start">
											<input
												class="w-full bg-transparent outline-none py-0.5"
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

		<hr class=" border-gray-50 dark:border-gray-850 my-2" />

		<div class="mt-2 space-y-3">
			<div>
				<div class="mb-2">
					<div class="flex justify-between items-center text-xs">
						<div class=" text-sm font-medium">{$i18n.t('Manage Models')}</div>
					</div>
				</div>
				<div class=" space-y-1 mb-3">
					<div class="mb-2">
						<div class="flex justify-between items-center text-xs">
							<div class=" text-xs font-medium">{$i18n.t('Default Model')}</div>
						</div>
					</div>

					<div class="flex-1 mr-2">
						<select
							class="w-full bg-transparent outline-none py-0.5"
							bind:value={defaultModelId}
							placeholder="Select a model"
						>
							<option value="" disabled selected>{$i18n.t('Select a model')}</option>
							{#each $models.filter((model) => model.id) as model}
								<option value={model.id} class="bg-gray-100 dark:bg-gray-700">{model.name}</option>
							{/each}
						</select>
					</div>
				</div>

				<div class=" space-y-1">
					<div class="mb-2">
						<div class="flex justify-between items-center text-xs my-3 pr-2">
							<div class=" text-xs font-medium">{$i18n.t('Model Whitelisting')}</div>

							<Switch bind:state={whitelistEnabled} />
						</div>
					</div>

					{#if whitelistEnabled}
						<div>
							<div class=" space-y-1.5">
								{#each whitelistModels as modelId, modelIdx}
									<div class="flex w-full">
										<div class="flex-1 mr-2">
											<select
												class="w-full bg-transparent outline-none py-0.5"
												bind:value={modelId}
												placeholder="Select a model"
											>
												<option value="" disabled selected>{$i18n.t('Select a model')}</option>
												{#each $models.filter((model) => model.id) as model}
													<option value={model.id} class="bg-gray-100 dark:bg-gray-700"
														>{model.name}</option
													>
												{/each}
											</select>
										</div>

										{#if modelIdx === 0}
											<button
												class="px-2.5 bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-900 dark:text-white rounded-lg transition"
												type="button"
												on:click={() => {
													if (whitelistModels.at(-1) !== '') {
														whitelistModels = [...whitelistModels, ''];
													}
												}}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													viewBox="0 0 16 16"
													fill="currentColor"
													class="w-4 h-4"
												>
													<path
														d="M8.75 3.75a.75.75 0 0 0-1.5 0v3.5h-3.5a.75.75 0 0 0 0 1.5h3.5v3.5a.75.75 0 0 0 1.5 0v-3.5h3.5a.75.75 0 0 0 0-1.5h-3.5v-3.5Z"
													/>
												</svg>
											</button>
										{:else}
											<button
												class="px-2.5 bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-900 dark:text-white rounded-lg transition"
												type="button"
												on:click={() => {
													whitelistModels.splice(modelIdx, 1);
													whitelistModels = whitelistModels;
												}}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													viewBox="0 0 16 16"
													fill="currentColor"
													class="w-4 h-4"
												>
													<path d="M3.75 7.25a.75.75 0 0 0 0 1.5h8.5a.75.75 0 0 0 0-1.5h-8.5Z" />
												</svg>
											</button>
										{/if}
									</div>
								{/each}
							</div>

							<div class="flex justify-end items-center text-xs mt-1.5 text-right">
								<div class=" text-xs font-medium">
									{whitelistModels.length}
									{$i18n.t('Model(s) Whitelisted')}
								</div>
							</div>
						</div>
					{/if}
				</div>
			</div>
		</div>
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
