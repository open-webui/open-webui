<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';

	import { user, config, settings } from '$lib/stores';
	import { updateUserProfile, createAPIKey, getAPIKey, getSessionUser } from '$lib/apis/auths';

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

	let APIKey = '';
	let APIKeyCopied = false;
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

	const createAPIKeyHandler = async () => {
		APIKey = await createAPIKey(localStorage.token);
		if (APIKey) {
			toast.success($i18n.t('API Key created.'));
		} else {
			toast.error($i18n.t('Failed to create API Key.'));
		}
	};

	onMount(async () => {
		name = $user?.name;
		profileImageUrl = $user?.profile_image_url;
		webhookUrl = $settings?.notifications?.webhook_url ?? '';

		APIKey = await getAPIKey(localStorage.token).catch((error) => {
			console.log(error);
			return '';
		});
	});
</script>

<div class="flex flex-col h-full justify-between">
	<div class="space-y-6 overflow-y-auto">
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

		<!-- Profile Section -->
		<div class="space-y-4">
			<div>
				<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-1">
					{$i18n.t('Profile')}
				</h3>
				<p class="text-sm text-gray-500 dark:text-gray-400">
					Manage your personal information
				</p>
			</div>

			<!-- Profile Image Card -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-start gap-4">
					<button
						class="relative rounded-full flex-shrink-0 group"
						type="button"
						on:click={() => {
							profileImageInputElement.click();
						}}
					>
						<img
							src={profileImageUrl !== '' ? profileImageUrl : generateInitialsImage(name)}
							alt="profile"
							class="rounded-full w-20 h-20 object-cover border-2 border-gray-200 dark:border-gray-700"
						/>

						<div
							class="absolute flex justify-center items-center rounded-full inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-60 transition-all duration-200"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="w-6 h-6 text-white opacity-0 group-hover:opacity-100 transition-opacity"
							>
								<path
									d="m2.695 14.762-1.262 3.155a.5.5 0 0 0 .65.65l3.155-1.262a4 4 0 0 0 1.343-.886L17.5 5.501a2.121 2.121 0 0 0-3-3L3.58 13.419a4 4 0 0 0-.885 1.343Z"
								/>
							</svg>
						</div>
					</button>

					<div class="flex-1">
						<div class="text-sm font-medium text-gray-900 dark:text-white mb-2">
							{$i18n.t('Profile Image')}
						</div>
						<div class="flex flex-wrap gap-2">
							<button
								class="px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
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
								}}
							>
								{$i18n.t('Use Initials')}
							</button>

							<button
								class="px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
								on:click={async () => {
									const url = await getGravatarUrl(localStorage.token, $user?.email);
									profileImageUrl = url;
								}}
							>
								{$i18n.t('Use Gravatar')}
							</button>

							<button
								class="px-3 py-1.5 text-xs font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
								on:click={async () => {
									profileImageUrl = '/user.png';
								}}
							>
								{$i18n.t('Remove')}
							</button>
						</div>
					</div>
				</div>
			</div>

			<!-- Name Input Card -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="text-sm font-medium text-gray-900 dark:text-white mb-2">
					{$i18n.t('Name')}
				</div>
				<input
					class="w-full px-3 py-2 text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
					type="text"
					bind:value={name}
					required
					placeholder={$i18n.t('Enter your name')}
				/>
			</div>

			{#if $config?.features?.enable_user_webhooks}
				<!-- Webhook URL Card -->
				<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
					<div class="text-sm font-medium text-gray-900 dark:text-white mb-1">
						{$i18n.t('Notification Webhook')}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mb-2">
						Receive notifications via webhook
					</div>
					<input
						class="w-full px-3 py-2 text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
						type="url"
						placeholder={$i18n.t('Enter your webhook URL')}
						bind:value={webhookUrl}
						required
					/>
				</div>
			{/if}
		</div>

		<!-- Password Section -->
		<div class="space-y-4 pt-2">
			<div>
				<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-1">
					{$i18n.t('Security')}
				</h3>
				<p class="text-sm text-gray-500 dark:text-gray-400">
					Manage your password and authentication
				</p>
			</div>

			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<UpdatePassword />
			</div>
		</div>

		<!-- API Keys Section -->
		<div class="space-y-4 pt-2">
			<div class="flex items-center justify-between">
				<div>
					<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-1">
						{$i18n.t('API keys')}
					</h3>
					<p class="text-sm text-gray-500 dark:text-gray-400">
						Manage your authentication tokens
					</p>
				</div>
				<button
					class="text-sm font-medium text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
					type="button"
					on:click={() => {
						showAPIKeys = !showAPIKeys;
					}}
				>
					{showAPIKeys ? $i18n.t('Hide') : $i18n.t('Show')}
				</button>
			</div>

			{#if showAPIKeys}
				<div class="space-y-3">
					<!-- JWT Token Card -->
					<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
						<div class="text-sm font-medium text-gray-900 dark:text-white mb-2">
							{$i18n.t('JWT Token')}
						</div>
						<div class="flex gap-2">
							<div class="flex-1">
								<SensitiveInput value={localStorage.token} readOnly={true} />
							</div>
							<button
								class="flex-shrink-0 p-2 rounded-lg bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
								on:click={() => {
									copyToClipboard(localStorage.token);
									JWTTokenCopied = true;
									setTimeout(() => {
										JWTTokenCopied = false;
									}, 2000);
								}}
								title="Copy to clipboard"
							>
								{#if JWTTokenCopied}
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 20 20"
										fill="currentColor"
										class="w-4 h-4 text-green-600 dark:text-green-400"
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
										class="w-4 h-4 text-gray-600 dark:text-gray-400"
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

					{#if $config?.features?.enable_api_key ?? true}
						<!-- API Key Card -->
						<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
							<div class="text-sm font-medium text-gray-900 dark:text-white mb-2">
								{$i18n.t('API Key')}
							</div>
							{#if APIKey}
								<div class="flex gap-2">
									<div class="flex-1">
										<SensitiveInput value={APIKey} readOnly={true} />
									</div>
									<button
										class="flex-shrink-0 p-2 rounded-lg bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
										on:click={() => {
											copyToClipboard(APIKey);
											APIKeyCopied = true;
											setTimeout(() => {
												APIKeyCopied = false;
											}, 2000);
										}}
										title="Copy to clipboard"
									>
										{#if APIKeyCopied}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 20 20"
												fill="currentColor"
												class="w-4 h-4 text-green-600 dark:text-green-400"
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
												class="w-4 h-4 text-gray-600 dark:text-gray-400"
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
											class="flex-shrink-0 p-2 rounded-lg bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
											on:click={() => {
												createAPIKeyHandler();
											}}
											title="Regenerate API key"
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="2"
												stroke="currentColor"
												class="w-4 h-4 text-gray-600 dark:text-gray-400"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99"
												/>
											</svg>
										</button>
									</Tooltip>
								</div>
							{:else}
								<button
									class="flex items-center justify-center gap-2 w-full px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
									on:click={() => {
										createAPIKeyHandler();
									}}
								>
									<Plus strokeWidth="2" className="w-4 h-4" />
									{$i18n.t('Create new secret key')}
								</button>
							{/if}
						</div>
					{/if}
				</div>
			{/if}
		</div>
	</div>

	<!-- Save Button -->
	<div class="flex justify-end pt-6 border-t border-gray-200 dark:border-gray-700 mt-6">
		<button
			class="px-6 py-2.5 text-sm font-medium bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors shadow-sm hover:shadow-md focus:outline-none focus:ring-2 focus:ring-orange-500 focus:ring-offset-2"
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

<style>
	/* Custom scrollbar styling */
	::-webkit-scrollbar {
		width: 8px;
		height: 8px;
	}

	::-webkit-scrollbar-track {
		background: transparent;
	}

	::-webkit-scrollbar-thumb {
		background: rgba(156, 163, 175, 0.5);
		border-radius: 4px;
	}

	::-webkit-scrollbar-thumb:hover {
		background: rgba(156, 163, 175, 0.7);
	}

	:global(.dark) ::-webkit-scrollbar-thumb {
		background: rgba(75, 85, 99, 0.5);
	}

	:global(.dark) ::-webkit-scrollbar-thumb:hover {
		background: rgba(75, 85, 99, 0.7);
	}
</style>