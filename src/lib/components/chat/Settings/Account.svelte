<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';

	import { user, config, settings } from '$lib/stores';
	import { updateUserProfile, createAPIKey, getAPIKey, getSessionUser } from '$lib/apis/auths';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import UpdatePassword from './Account/UpdatePassword.svelte';
	import { getGravatarUrl } from '$lib/apis/utils';
	import { generateInitialsImage, canvasPixelTest } from '$lib/utils';
	import { copyToClipboard } from '$lib/utils';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import UserProfileImage from './Account/UserProfileImage.svelte';
	import UserSettingField from './UserSettingField.svelte';
	import UserSettingRow from './UserSettingRow.svelte';
	import UserSettingSection from './UserSettingSection.svelte';

	const i18n = getContext('i18n');

	export let saveHandler: Function;
	export let saveSettings: Function;

	let profileImageUrl = '';
	let name = '';
	let bio = '';

	let _gender = '';
	let gender = '';
	let dateOfBirth = '';

	let webhookUrl = '';
	let showAPIKeys = false;

	let JWTTokenCopied = false;

	let APIKey = '';
	let APIKeyCopied = false;

	const textareaClass =
		'w-full resize-y rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';
	const inputClass =
		'h-7 w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';
	const actionButtonClass =
		'text-xs text-gray-500 transition-colors hover:text-gray-900 dark:text-gray-500 dark:hover:text-white';

	const submitHandler = async () => {
		if (name !== $user?.name) {
			if (profileImageUrl === generateInitialsImage($user?.name) || profileImageUrl === '') {
				profileImageUrl = generateInitialsImage(name);
			}
		}

		if (webhookUrl !== $settings?.notifications?.webhook_url) {
			saveSettings({
				notifications: {
					...$settings.notifications,
					webhook_url: webhookUrl
				}
			});
		}

		const updatedUser = await updateUserProfile(localStorage.token, {
			name: name,
			profile_image_url: profileImageUrl,
			bio: bio ? bio : null,
			gender: gender ? gender : null,
			date_of_birth: dateOfBirth ? dateOfBirth : null
		}).catch((error) => {
			toast.error(`${error}`);
		});

		if (updatedUser) {
			// Get Session User Info
			const sessionUser = await getSessionUser(localStorage.token).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			await user.set(sessionUser);
			return true;
		}
		return false;
	};

	const createAPIKeyHandler = async () => {
		APIKey = await createAPIKey(localStorage.token);
		if (APIKey) {
			toast.success($i18n.t('API Key created.'));
		} else {
			toast.error($i18n.t('Failed to create API Key.'));
		}
	};

	onMount(async () => {
		const user = await getSessionUser(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (user) {
			name = user?.name ?? '';
			profileImageUrl = user?.profile_image_url ?? '';
			bio = user?.bio ?? '';

			_gender = user?.gender ?? '';
			gender = _gender;

			dateOfBirth = user?.date_of_birth ?? '';
		}

		webhookUrl = $settings?.notifications?.webhook_url ?? '';

		// Only fetch API key if the feature is enabled and user has permission
		if (
			user &&
			($config?.features?.enable_api_keys ?? true) &&
			(user?.role === 'admin' || (user?.permissions?.features?.api_keys ?? false))
		) {
			APIKey = await getAPIKey(localStorage.token).catch((error) => {
				console.log(error);
				return '';
			});
		}
	});
</script>

<div id="tab-account" class="flex h-full flex-col text-sm">
	<div class="flex-1 min-h-0 w-full overflow-y-auto scrollbar-hover pr-1.5">
		<h2 class="mb-4 text-sm font-medium text-gray-900 dark:text-white">{$i18n.t('Account')}</h2>

		<UserSettingSection title={$i18n.t('Profile')} first>
			<UserProfileImage
				bind:profileImageUrl
				user={$user}
				variant="account"
				displayName={$user?.name}
			/>

			<UserSettingField
				label={$i18n.t('Name')}
				description={$i18n.t('Set the display name shown across your account.')}
			>
				<input
					class={inputClass}
					type="text"
					bind:value={name}
					aria-label={$i18n.t('Name')}
					required
					placeholder={$i18n.t('Enter your name')}
				/>
			</UserSettingField>

			<UserSettingField
				label={$i18n.t('Bio')}
				description={$i18n.t('Add optional profile context visible where profiles are shown.')}
			>
				<Textarea
					className={textareaClass}
					minSize={60}
					bind:value={bio}
					ariaLabel={$i18n.t('Bio')}
					placeholder={$i18n.t('Share your background and interests')}
				/>
			</UserSettingField>

			<UserSettingField
				label={$i18n.t('Gender')}
				description={$i18n.t('Choose the gender value stored on your profile.')}
			>
				<select
					class={inputClass}
					bind:value={_gender}
					aria-label={$i18n.t('Gender')}
					on:change={(e) => {
						console.log(_gender);

						if (_gender === 'custom') {
							// Handle custom gender input
							gender = '';
						} else {
							gender = _gender;
						}
					}}
				>
					<option value="" selected>{$i18n.t('Prefer not to say')}</option>
					<option value="male">{$i18n.t('Male')}</option>
					<option value="female">{$i18n.t('Female')}</option>
					<option value="custom">{$i18n.t('Custom')}</option>
				</select>

				{#if _gender === 'custom'}
					<input
						class="mt-1 {inputClass}"
						type="text"
						required
						aria-label={$i18n.t('Custom Gender')}
						placeholder={$i18n.t('Enter your gender')}
						bind:value={gender}
					/>
				{/if}
			</UserSettingField>

			<UserSettingField
				label={$i18n.t('Birth Date')}
				description={$i18n.t('Set the birth date saved with your profile.')}
			>
				<input
					class={inputClass}
					type="date"
					aria-label={$i18n.t('Birth Date')}
					bind:value={dateOfBirth}
					required
				/>
			</UserSettingField>
		</UserSettingSection>

		{#if $config?.features?.enable_user_webhooks && ($user?.role === 'admin' || ($user?.permissions?.features?.webhooks ?? false))}
			<UserSettingSection title={$i18n.t('Notifications')}>
				<UserSettingField
					label={$i18n.t('Notification Webhook')}
					description={$i18n.t('Send account notifications to this webhook URL.')}
				>
					<input
						class={inputClass}
						type="url"
						placeholder={$i18n.t('Enter your webhook URL')}
						aria-label={$i18n.t('Notification Webhook')}
						bind:value={webhookUrl}
						required
					/>
				</UserSettingField>
			</UserSettingSection>
		{/if}

		{#if $config?.features.enable_login_form && $config?.features.enable_password_change_form}
			<UserSettingSection title={$i18n.t('Password')}>
				<UpdatePassword />
			</UserSettingSection>
		{/if}

		{#if ($config?.features?.enable_api_keys ?? true) && ($user?.role === 'admin' || ($user?.permissions?.features?.api_keys ?? false))}
			<UserSettingSection title={$i18n.t('API keys')}>
				<UserSettingRow description={$i18n.t('Show or hide sensitive account secrets.')}>
					<span slot="label">{$i18n.t('Secrets')}</span>
					<button
						class={actionButtonClass}
						type="button"
						on:click={() => {
							showAPIKeys = !showAPIKeys;
						}}>{showAPIKeys ? $i18n.t('Hide') : $i18n.t('Show')}</button
					>
				</UserSettingRow>

				{#if showAPIKeys}
					<div class="flex flex-col gap-2.5">
						{#if $user?.role === 'admin'}
							<UserSettingField
								label={$i18n.t('JWT Token')}
								description={$i18n.t('Copy the current session token for authenticated requests.')}
							>
								<div class="flex">
									<SensitiveInput value={localStorage.token} readOnly={true} />

									<button
										class="ml-1.5 rounded-sm px-1.5 py-1 text-gray-500 transition hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-gray-850 dark:hover:text-gray-300"
										aria-label={$i18n.t('Copy Token')}
										on:click={() => {
											copyToClipboard(localStorage.token);
											JWTTokenCopied = true;
											setTimeout(() => {
												JWTTokenCopied = false;
											}, 2000);
										}}
									>
										{#if JWTTokenCopied}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 20 20"
												fill="currentColor"
												class="w-4 h-4"
											>
												<path
													fill-rule="evenodd"
													d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
													clip-rule="evenodd"
												/>
											</svg>
										{:else}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 16 16"
												fill="currentColor"
												class="w-4 h-4"
											>
												<path
													fill-rule="evenodd"
													d="M11.986 3H12a2 2 0 0 1 2 2v6a2 2 0 0 1-1.5 1.937V7A2.5 2.5 0 0 0 10 4.5H4.063A2 2 0 0 1 6 3h.014A2.25 2.25 0 0 1 8.25 1h1.5a2.25 2.25 0 0 1 2.236 2ZM10.5 4v-.75a.75.75 0 0 0-.75-.75h-1.5a.75.75 0 0 0-.75.75V4h3Z"
													clip-rule="evenodd"
												/>
												<path
													fill-rule="evenodd"
													d="M3 6a1 1 0 0 0-1 1v7a1 1 0 0 0 1 1h7a1 1 0 0 0 1-1V7a1 1 0 0 0-1-1H3Zm1.75 2.5a.75.75 0 0 0 0 1.5h3.5a.75.75 0 0 0 0-1.5h-3.5ZM4 11.75a.75.75 0 0 1 .75-.75h3.5a.75.75 0 0 1 0 1.5h-3.5a.75.75 0 0 1-.75-.75Z"
													clip-rule="evenodd"
												/>
											</svg>
										{/if}
									</button>
								</div>
							</UserSettingField>
						{/if}

						{#if ($config?.features?.enable_api_keys ?? true) && ($user?.role === 'admin' || ($user?.permissions?.features?.api_keys ?? false))}
							<UserSettingField
								label={$i18n.t('API Key')}
								description={$i18n.t('Create, copy, or rotate your API key.')}
							>
								<div class="flex">
									{#if APIKey}
										<SensitiveInput value={APIKey} readOnly={true} />

										<button
											class="ml-1.5 rounded-sm px-1.5 py-1 text-gray-500 transition hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-gray-850 dark:hover:text-gray-300"
											aria-label={$i18n.t('Copy API Key')}
											on:click={() => {
												copyToClipboard(APIKey);
												APIKeyCopied = true;
												setTimeout(() => {
													APIKeyCopied = false;
												}, 2000);
											}}
										>
											{#if APIKeyCopied}
												<svg
													xmlns="http://www.w3.org/2000/svg"
													viewBox="0 0 20 20"
													fill="currentColor"
													class="w-4 h-4"
												>
													<path
														fill-rule="evenodd"
														d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
														clip-rule="evenodd"
													/>
												</svg>
											{:else}
												<svg
													xmlns="http://www.w3.org/2000/svg"
													viewBox="0 0 16 16"
													fill="currentColor"
													class="w-4 h-4"
												>
													<path
														fill-rule="evenodd"
														d="M11.986 3H12a2 2 0 0 1 2 2v6a2 2 0 0 1-1.5 1.937V7A2.5 2.5 0 0 0 10 4.5H4.063A2 2 0 0 1 6 3h.014A2.25 2.25 0 0 1 8.25 1h1.5a2.25 2.25 0 0 1 2.236 2ZM10.5 4v-.75a.75.75 0 0 0-.75-.75h-1.5a.75.75 0 0 0-.75.75V4h3Z"
														clip-rule="evenodd"
													/>
													<path
														fill-rule="evenodd"
														d="M3 6a1 1 0 0 0-1 1v7a1 1 0 0 0 1 1h7a1 1 0 0 0 1-1V7a1 1 0 0 0-1-1H3Zm1.75 2.5a.75.75 0 0 0 0 1.5h3.5a.75.75 0 0 0 0-1.5h-3.5ZM4 11.75a.75.75 0 0 1 .75-.75h3.5a.75.75 0 0 1 0 1.5h-3.5a.75.75 0 0 1-.75-.75Z"
														clip-rule="evenodd"
													/>
												</svg>
											{/if}
										</button>

										<Tooltip content={$i18n.t('Create new key')}>
											<button
												class="rounded-sm px-1.5 py-1 text-gray-500 transition hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-gray-850 dark:hover:text-gray-300"
												aria-label={$i18n.t('Create new key')}
												on:click={() => {
													createAPIKeyHandler();
												}}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													fill="none"
													viewBox="0 0 24 24"
													stroke-width="2"
													stroke="currentColor"
													class="size-4"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99"
													/>
												</svg>
											</button>
										</Tooltip>
									{:else}
										<button
											class={actionButtonClass}
											on:click={() => {
												createAPIKeyHandler();
											}}
										>
											<Plus strokeWidth="2" className=" size-3.5" />

											{$i18n.t('Create new secret key')}</button
										>
									{/if}
								</div>
							</UserSettingField>
						{/if}
					</div>
				{/if}
			</UserSettingSection>
		{/if}
	</div>

	<div class="shrink-0 flex w-full justify-end pt-3 text-sm font-normal">
		<button
			class="px-3.5 py-1.5 text-sm font-normal bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			on:click={async () => {
				const res = await submitHandler();

				if (res) {
					saveHandler();
				}
			}}
		>
			{$i18n.t('Save')}
		</button>
	</div>
</div>
