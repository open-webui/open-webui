<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';

	import { user, config, settings } from '$lib/stores';
	import {
		updateUserProfile,
		getSessionUser,
		getAPIKeys,
		createAPIKeyWithName,
		deleteAPIKeyById,
		getAPIKeyExpiryInfo
	} from '$lib/apis/auths';

	import UpdatePassword from './Account/UpdatePassword.svelte';
	import { getGravatarUrl } from '$lib/apis/utils';
	import { generateInitialsImage, canvasPixelTest } from '$lib/utils';
	import { copyToClipboard } from '$lib/utils';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';

	const i18n = getContext('i18n');

	export let saveHandler: Function;
	export let saveSettings: Function;

	let profileImageUrl = '';
	let name = '';

	let webhookUrl = '';
	let showAPIKeys = false;

	let JWTTokenCopied = false;

	// Multiple API Keys support
	let apiKeys = [];
	let expiryInfo = null;
	let showCreateKeyModal = false;
	let newKeyName = '';
	let copiedKeyIds = new Set();

	let profileImageInputElement: HTMLInputElement;

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

		const updatedUser = await updateUserProfile(localStorage.token, name, profileImageUrl).catch(
			(error) => {
				toast.error(`${error}`);
			}
		);

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

	const loadAPIKeys = async () => {
		try {
			apiKeys = await getAPIKeys(localStorage.token);
			expiryInfo = await getAPIKeyExpiryInfo(localStorage.token);
		} catch (error) {
			console.error('Failed to load API keys:', error);
		}
	};

	const createNewAPIKey = async () => {
		try {
			const newKey = await createAPIKeyWithName(localStorage.token, newKeyName.trim() || undefined);
			if (newKey) {
				toast.success($i18n.t('API Key created successfully.'));
				await loadAPIKeys();
				showCreateKeyModal = false;
				newKeyName = '';
			}
		} catch (error) {
			toast.error($i18n.t('Failed to create API Key.'));
			console.error('Failed to create API key:', error);
		}
	};

	const deleteAPIKeyHandler = async (keyId) => {
		try {
			await deleteAPIKeyById(localStorage.token, keyId);
			toast.success($i18n.t('API Key deleted successfully.'));
			await loadAPIKeys();
		} catch (error) {
			toast.error($i18n.t('Failed to delete API Key.'));
			console.error('Failed to delete API key:', error);
		}
	};

	const copyAPIKey = (keyValue, keyId) => {
		copyToClipboard(keyValue);
		copiedKeyIds.add(keyId);
		copiedKeyIds = copiedKeyIds; // trigger reactivity
		setTimeout(() => {
			copiedKeyIds.delete(keyId);
			copiedKeyIds = copiedKeyIds; // trigger reactivity
		}, 2000);
	};

	const formatDate = (dateInSeconds) => {
		if (!dateInSeconds) return 'N/A';
		return new Date(dateInSeconds * 1000).toLocaleString();
	};

	const isKeyExpired = (key) => {
		if (!expiryInfo || !expiryInfo.expiry_enabled) return false;
		if (!key.expires_at) return false;
		return new Date(key.expires_at * 1000) < new Date();
	};

	const formatExpiryDuration = (expiryInSeconds) => {
		if (!expiryInSeconds || expiryInSeconds <= 0) {
			return '';
		}
		if (expiryInSeconds >= 86400) {
			const days = Math.floor(expiryInSeconds / 86400);
			return `${days} day${days > 1 ? 's' : ''}`;
		}
		if (expiryInSeconds >= 3600) {
			const hours = Math.floor(expiryInSeconds / 3600);
			return `${hours} hour${hours > 1 ? 's' : ''}`;
		}
		if (expiryInSeconds >= 60) {
			const minutes = Math.floor(expiryInSeconds / 60);
			return `${minutes} minute${minutes > 1 ? 's' : ''}`;
		}
		return `${expiryInSeconds} second${expiryInSeconds !== 1 ? 's' : ''}`;
	};

	onMount(async () => {
		name = $user?.name;
		profileImageUrl = $user?.profile_image_url;
		webhookUrl = $settings?.notifications?.webhook_url ?? '';

		// Load multiple API keys
		await loadAPIKeys();
	});
</script>

<div id="tab-account" class="flex flex-col h-full justify-between text-sm">
	<div class=" overflow-y-scroll max-h-[28rem] lg:max-h-full">
		<input
			id="profile-image-input"
			bind:this={profileImageInputElement}
			type="file"
			hidden
			accept="image/*"
			on:change={(e) => {
				const files = profileImageInputElement.files ?? [];
				let reader = new FileReader();
				reader.onload = (event) => {
					let originalImageUrl = `${event.target.result}`;

					const img = new Image();
					img.src = originalImageUrl;

					img.onload = function () {
						const canvas = document.createElement('canvas');
						const ctx = canvas.getContext('2d');

						// Calculate the aspect ratio of the image
						const aspectRatio = img.width / img.height;

						// Calculate the new width and height to fit within 250x250
						let newWidth, newHeight;
						if (aspectRatio > 1) {
							newWidth = 250 * aspectRatio;
							newHeight = 250;
						} else {
							newWidth = 250;
							newHeight = 250 / aspectRatio;
						}

						// Set the canvas size
						canvas.width = 250;
						canvas.height = 250;

						// Calculate the position to center the image
						const offsetX = (250 - newWidth) / 2;
						const offsetY = (250 - newHeight) / 2;

						// Draw the image on the canvas
						ctx.drawImage(img, offsetX, offsetY, newWidth, newHeight);

						// Get the base64 representation of the compressed image
						const compressedSrc = canvas.toDataURL('image/jpeg');

						// Display the compressed image
						profileImageUrl = compressedSrc;

						profileImageInputElement.files = null;
					};
				};

				if (
					files.length > 0 &&
					['image/gif', 'image/webp', 'image/jpeg', 'image/png'].includes(files[0]['type'])
				) {
					reader.readAsDataURL(files[0]);
				}
			}}
		/>

		<div class="space-y-1">
			<!-- <div class=" text-sm font-medium">{$i18n.t('Account')}</div> -->

			<div class="flex space-x-5">
				<div class="flex flex-col">
					<div class="self-center mt-2">
						<button
							class="relative rounded-full dark:bg-gray-700"
							type="button"
							on:click={() => {
								profileImageInputElement.click();
							}}
						>
							<img
								src={profileImageUrl !== '' ? profileImageUrl : generateInitialsImage(name)}
								alt="profile"
								class=" rounded-full size-16 object-cover"
							/>

							<div
								class="absolute flex justify-center rounded-full bottom-0 left-0 right-0 top-0 h-full w-full overflow-hidden bg-gray-700 bg-fixed opacity-0 transition duration-300 ease-in-out hover:opacity-50"
							>
								<div class="my-auto text-gray-100">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 20 20"
										fill="currentColor"
										class="w-5 h-5"
									>
										<path
											d="m2.695 14.762-1.262 3.155a.5.5 0 0 0 .65.65l3.155-1.262a4 4 0 0 0 1.343-.886L17.5 5.501a2.121 2.121 0 0 0-3-3L3.58 13.419a4 4 0 0 0-.885 1.343Z"
										/>
									</svg>
								</div>
							</div>
						</button>
					</div>
				</div>

				<div class="flex-1 flex flex-col self-center gap-0.5">
					<div class=" mb-0.5 text-sm font-medium">{$i18n.t('Profile Image')}</div>

					<div>
						<button
							class=" text-xs text-center text-gray-800 dark:text-gray-400 rounded-full px-4 py-0.5 bg-gray-100 dark:bg-gray-850"
							on:click={async () => {
								if (canvasPixelTest()) {
									profileImageUrl = generateInitialsImage(name);
								} else {
									toast.info(
										$i18n.t(
											'Fingerprint spoofing detected: Unable to use initials as avatar. Defaulting to default profile image.'
										),
										{
											duration: 1000 * 10
										}
									);
								}
							}}>{$i18n.t('Use Initials')}</button
						>

						<button
							class=" text-xs text-center text-gray-800 dark:text-gray-400 rounded-full px-4 py-0.5 bg-gray-100 dark:bg-gray-850"
							on:click={async () => {
								const url = await getGravatarUrl(localStorage.token, $user?.email);

								profileImageUrl = url;
							}}>{$i18n.t('Use Gravatar')}</button
						>

						<button
							class=" text-xs text-center text-gray-800 dark:text-gray-400 rounded-lg px-2 py-1"
							on:click={async () => {
								profileImageUrl = '/user.png';
							}}>{$i18n.t('Remove')}</button
						>
					</div>
				</div>
			</div>

			<div class="pt-0.5">
				<div class="flex flex-col w-full">
					<div class=" mb-1 text-xs font-medium">{$i18n.t('Name')}</div>

					<div class="flex-1">
						<input
							class="w-full text-sm dark:text-gray-300 bg-transparent outline-hidden"
							type="text"
							bind:value={name}
							required
							placeholder={$i18n.t('Enter your name')}
						/>
					</div>
				</div>
			</div>

			{#if $config?.features?.enable_user_webhooks}
				<div class="pt-2">
					<div class="flex flex-col w-full">
						<div class=" mb-1 text-xs font-medium">{$i18n.t('Notification Webhook')}</div>

						<div class="flex-1">
							<input
								class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden"
								type="url"
								placeholder={$i18n.t('Enter your webhook URL')}
								bind:value={webhookUrl}
								required
							/>
						</div>
					</div>
				</div>
			{/if}
		</div>

		<hr class="border-gray-50 dark:border-gray-850 my-2" />

		<div class="my-2">
			<UpdatePassword />
		</div>

		{#if ($config?.features?.enable_api_key ?? true) || $user?.role === 'admin'}
			<div class="flex justify-between items-center text-sm mb-2">
				<div class="font-medium">{$i18n.t('API keys')}</div>
				<button
					class="text-xs font-medium text-gray-500"
					type="button"
					on:click={() => {
						showAPIKeys = !showAPIKeys;
					}}>{showAPIKeys ? $i18n.t('Hide') : $i18n.t('Show')}</button
				>
			</div>

			{#if showAPIKeys}
				<div class="flex flex-col gap-4">
					{#if $user?.role === 'admin'}
						<div class="justify-between w-full">
							<div class="flex justify-between w-full">
								<div class="self-center text-xs font-medium mb-1">{$i18n.t('JWT Token')}</div>
							</div>

							<div class="flex">
								<SensitiveInput value={localStorage.token} readOnly={true} />

								<button
									class="ml-1.5 px-1.5 py-1 dark:hover:bg-gray-850 transition rounded-lg"
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
						</div>
					{/if}

					{#if $config?.features?.enable_api_key ?? true}
						<div class="w-full">
							<!-- Expiry Info -->
							{#if expiryInfo && expiryInfo.expiry_enabled}
								<div class="mb-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
									<div class="text-xs font-medium text-blue-700 dark:text-blue-300 mb-1">
										{$i18n.t('API Key Expiration')}
									</div>
									<div class="text-xs text-blue-600 dark:text-blue-400">
										{$i18n.t('Keys expire after {{duration}}', {
											duration: formatExpiryDuration(expiryInfo.expiry)
										})}
									</div>
								</div>
							{/if}

							<!-- Create New Key Button -->
							<div class="mb-4">
								<button
									class="flex gap-1.5 items-center font-medium px-3.5 py-1.5 rounded-lg bg-gray-100/70 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition"
									on:click={() => {
										showCreateKeyModal = true;
									}}
								>
									<Plus strokeWidth="2" className="size-3.5" />
									{$i18n.t('Create new secret key')}
								</button>
							</div>

							<!-- API Keys List -->
							{#if apiKeys && apiKeys.length > 0}
								<div class="space-y-3">
									{#each apiKeys as apiKey}
										<div class="p-3 border border-gray-200 dark:border-gray-700 rounded-lg">
											<div class="flex justify-between items-start mb-2">
												<div class="flex-1">
													<div class="flex items-center gap-2 mb-1">
														<span class="text-sm font-medium">
															{apiKey.name || `API Key ${apiKey.id.slice(-8)}`}
														</span>
														{#if isKeyExpired(apiKey)}
															<span class="px-2 py-0.5 text-xs bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300 rounded-full">
																{$i18n.t('Expired')}
															</span>
														{:else if expiryInfo && expiryInfo.expiry_enabled}
															<span class="px-2 py-0.5 text-xs bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300 rounded-full">
																{$i18n.t('Active')}
															</span>
														{/if}
													</div>
													<div class="text-xs text-gray-500 dark:text-gray-400 space-y-1">
														<div>{$i18n.t('Created')}: {formatDate(apiKey.created_at)}</div>
														{#if apiKey.last_used_at}
															<div>{$i18n.t('Last used')}: {formatDate(apiKey.last_used_at)}</div>
														{/if}
														{#if apiKey.expires_at && expiryInfo && expiryInfo.expiry_enabled}
															<div class:text-red-500={isKeyExpired(apiKey)}>
																{$i18n.t('Expires')}: {formatDate(apiKey.expires_at)}
															</div>
														{/if}
													</div>
												</div>
												<button
													class="p-1 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition"
													on:click={() => deleteAPIKeyHandler(apiKey.id)}
													title={$i18n.t('Delete API Key')}
												>
													<svg
														xmlns="http://www.w3.org/2000/svg"
														viewBox="0 0 16 16"
														fill="currentColor"
														class="w-4 h-4"
													>
														<path
															fill-rule="evenodd"
															d="M5 3.25V4H2.75a.75.75 0 0 0 0 1.5h.3l.815 8.15A1.5 1.5 0 0 0 5.357 15h5.285a1.5 1.5 0 0 0 1.493-1.35L12.95 5.5h.3a.75.75 0 0 0 0-1.5H11V3.25a2.25 2.25 0 0 0-4.5 0ZM6.5 3.25a.75.75 0 0 1 1.5 0V4h-1.5V3.25ZM7.25 7a.75.75 0 0 1 1.5 0v5a.75.75 0 0 1-1.5 0V7ZM5.5 7a.75.75 0 0 0-1.5 0v5a.75.75 0 0 0 1.5 0V7Z"
															clip-rule="evenodd"
														/>
													</svg>
												</button>
											</div>
											<div class="flex">
												<SensitiveInput value={apiKey.api_key} readOnly={true} />
												<button
													class="ml-1.5 px-1.5 py-1 dark:hover:bg-gray-850 transition rounded-lg"
													on:click={() => copyAPIKey(apiKey.api_key, apiKey.id)}
												>
													{#if copiedKeyIds.has(apiKey.id)}
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
										</div>
									{/each}
								</div>
							{:else}
								<div class="text-center py-4 text-gray-500 dark:text-gray-400">
									<p class="text-sm">{$i18n.t('No API keys created yet.')}</p>
								</div>
							{/if}
						</div>
					{/if}
				</div>
			{/if}
		{/if}
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
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

<!-- Create API Key Modal -->
{#if showCreateKeyModal}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
		<div class="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md mx-4">
			<h3 class="text-lg font-semibold mb-4">{$i18n.t('Create New API Key')}</h3>
			
			<div class="mb-4">
				<label class="block text-sm font-medium mb-2" for="keyName">
					{$i18n.t('Key Name')} ({$i18n.t('Optional')})
				</label>
				<input
					id="keyName"
					type="text"
					class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:bg-gray-700 dark:text-gray-300 outline-hidden border border-gray-200 dark:border-gray-600"
					placeholder={$i18n.t('Enter a name for this API key')}
					bind:value={newKeyName}
					maxlength="50"
				/>
				<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
					{$i18n.t('Give your API key a descriptive name to help you identify it later.')}
				</p>
			</div>

			{#if expiryInfo && expiryInfo.expiry_enabled}
				<div class="mb-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
					<p class="text-sm text-yellow-700 dark:text-yellow-300">
						{$i18n.t('This key will expire after {{duration}}.', {
							duration: formatExpiryDuration(expiryInfo.expiry)
						})}
					</p>
				</div>
			{/if}

			<div class="flex justify-end gap-2">
				<button
					class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition"
					on:click={() => {
						showCreateKeyModal = false;
						newKeyName = '';
					}}
				>
					{$i18n.t('Cancel')}
				</button>
				<button
					class="px-4 py-2 text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 rounded-lg transition"
					on:click={createNewAPIKey}
				>
					{$i18n.t('Create Key')}
				</button>
			</div>
		</div>
	</div>
{/if}
