<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';

	import { user, config, settings } from '$lib/stores';
	import { updateUserProfile, createAPIKey, getAPIKey, deleteUserProfile } from '$lib/apis/auths';

	import UpdatePassword from './Account/UpdatePassword.svelte';
	import { getGravatarUrl } from '$lib/apis/utils';
	import { generateInitialsImage, canvasPixelTest } from '$lib/utils';
	import { copyToClipboard } from '$lib/utils';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import CameraIcon from '$lib/components/icons/CameraIcon.svelte';
	import DeleteIcon from '$lib/components/icons/DeleteIcon.svelte';
	import { updateUserPassword } from '$lib/apis/auths';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import DOMPurify from 'dompurify';

	const i18n = getContext('i18n');

	export let saveHandler: Function;
	export let saveSettings: Function;

	let profileImageUrl = '';
	let firstName = '';
	let lastName = '';
	let email = '';
	let loading = false;

	let webhookUrl = '';
	let showAPIKeys = false;

	let JWTTokenCopied = false;

	let APIKey = '';
	let APIKeyCopied = false;
	let profileImageInputElement: HTMLInputElement;

	let currentPassword = '';
	let newPassword = '';
	let newPasswordConfirm = '';

	let showDeleteConfirm = false;

	function isValidEmail(email: string): boolean {
		const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
		return regex.test(email);
	}

	const submitHandler = async () => {
		loading = true;
		if (firstName !== $user.first_name) {
			if (profileImageUrl === generateInitialsImage($user.first_name) || profileImageUrl === '') {
				profileImageUrl = generateInitialsImage(firstName);
			}
		}
		// if (email !== $user.email) {
		// 	if (!isValidEmail(email)) {
		// 		toast.error($i18n.t('Please enter valid email.'));
		// 		return;
		// 	}
		// }
		if (currentPassword) {
			if(!newPassword) {
				toast.error(
					`Please enter new password.`
				);
				return;
			}
			if (newPassword !== newPasswordConfirm) {
				toast.error(
					`The passwords you entered don't quite match. Please double-check and try again.`
				);
				newPassword = '';
				newPasswordConfirm = '';
				return;
			}
		}

		// if (webhookUrl !== $settings?.notifications?.webhook_url) {
		// 	saveSettings({
		// 		notifications: {
		// 			...$settings.notifications,
		// 			webhook_url: webhookUrl
		// 		}
		// 	});
		// }

		const password = newPassword ? newPassword : null;

		const updatedUser = await updateUserProfile(
			localStorage.token,
			firstName,
			profileImageUrl,
			lastName,
			email,
			password
		).catch((error) => {
			toast.error(`${error}`);
		});

		loading = false;

		if (updatedUser) {
			currentPassword = '';
			newPassword = '';
			newPasswordConfirm = '';
			await user.set(updatedUser);
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

	const deleteUserHandler = async () => {
		const userId = $user.id;
		await deleteUserProfile(localStorage.token, userId);
	}

	onMount(async () => {
		firstName = $user?.first_name ? $user?.first_name : '';
		email = $user?.email;
		lastName = $user?.last_name ? $user?.last_name : '';
		profileImageUrl = $user.profile_image_url;
		// webhookUrl = $settings?.notifications?.webhook_url ?? '';

		// APIKey = await getAPIKey(localStorage.token).catch((error) => {
		// 	console.log(error);
		// 	return '';
		// });
	});
</script>

<!-- space-y-3 overflow-y-scroll max-h-[28rem] lg:max-h-full -->
<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Are you sure you want to delete account?')}
	on:confirm={() => {
		deleteUserHandler();
	}}
	confirmLabel={$i18n.t('Delete Account')}
	>
	<div class=" text-sm text-gray-700 dark:text-gray-300 flex-1 line-clamp-3">
		{@html DOMPurify.sanitize(
			$i18n.t('This action is permanent and cannot be undone. All your data will be lost.')
		)}
	</div>
</DeleteConfirmDialog>
<div class="flex flex-col justify-between text-sm pt-5">
	<div class=" ">
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

		<div class="mb-4">
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
								src={profileImageUrl !== '' ? profileImageUrl : generateInitialsImage(firstName)}
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

				<div class="flex-1 flex flex-col self-center gap-0.5 mb-5">
					<div class=" mb-0.5 text-sm dark:text-customGray-100">{$i18n.t('Profile Picture')}</div>
					<div class="text-xs dark:text-customGray-100/50 mb-2">
						{$i18n.t('We only support PNGs, JPEGs and GIFs under 10MB')}
					</div>

					<div class="flex items-center">
						<button
							type="button"
							on:click={() => {
								profileImageInputElement.click();
							}}
							class="flex items-center font-medium text-xs dark:text-customGray-300 px-2 py-1 rounded-xl border border-customGray-700 dark:bg-customGray-900"
						>
							<CameraIcon className="size-4 mr-1" />
							{$i18n.t('Upload Image')}
						</button>
						<!-- <button
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
						> -->

						<!-- <button
							class=" text-xs text-center text-gray-800 dark:text-gray-400 rounded-full px-4 py-0.5 bg-gray-100 dark:bg-gray-850"
							on:click={async () => {
								const url = await getGravatarUrl($user.email);

								profileImageUrl = url;
							}}>{$i18n.t('Use Gravatar')}</button
						> -->

						<button
							class="flex items-center text-xs text-center text-gray-800 text-2xs dark:text-customGray-300 rounded-lg px-2 py-1"
							on:click={async () => {
								profileImageUrl = '/user.png';
							}}
							><DeleteIcon className="mr-1 size-4" />
							{$i18n.t('Remove')}</button
						>
					</div>
				</div>
			</div>

			<div class="pt-0.5">
				<div class="flex flex-col w-full mb-2.5">
					<div class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md">
						{#if firstName}
							<div class="text-xs absolute text-lightGray-100/50 left-2.5 top-1 dark:text-customGray-100/50">
								{$i18n.t('First Name')}
							</div>
						{/if}
						<input
							class={`px-2.5 text-sm ${firstName ? 'pt-2' : 'pt-0'} text-lightGray-100 placeholder:text-lightGray-100 w-full h-12 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none`}
							placeholder={$i18n.t('First Name')}
							bind:value={firstName}
						/>
					</div>
				</div>
				<div class="flex flex-col w-full mb-2.5">
					<div class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md">
						{#if lastName}
							<div class="text-xs absolute left-2.5 top-1 text-lightGray-100/50 dark:text-customGray-100/50">
								{$i18n.t('Last Name')}
							</div>
						{/if}
						<input
							class={`px-2.5 text-sm ${lastName ? 'mt-2' : 'pt-0'} text-lightGray-100 placeholder:text-lightGray-100 w-full h-12 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none`}
							placeholder={$i18n.t('Last Name')}
							bind:value={lastName}
						/>
					</div>
				</div>
				<!-- <div class="flex flex-col w-full">
					<div class="relative w-full dark:bg-customGray-900 rounded-md">
						{#if email}
							<div class="text-xs absolute left-2.5 top-1 dark:text-customGray-100/50">
								{$i18n.t('Primary Email Address')}
							</div>
						{/if}
						<input
							class={`px-2.5 text-sm ${email ? 'mt-2' : 'mt-0'} w-full h-10 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none`}
							placeholder={$i18n.t('Primary Email Address')}
							bind:value={email}
							type="email"
							disabled
						/>
					</div>
				</div> -->
			</div>

			<!-- <div class="pt-2">
				<div class="flex flex-col w-full">
					<div class=" mb-1 text-xs font-medium">{$i18n.t('Notification Webhook')}</div>

					<div class="flex-1">
						<input
							class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
							type="url"
							placeholder={$i18n.t('Enter your webhook URL')}
							bind:value={webhookUrl}
							required
						/>
					</div>
				</div>
			</div> -->
		</div>

		<div>
			<div
				class="flex w-full justify-between items-center py-2.5 border-b border-lightGray-400 dark:border-customGray-700 mb-2"
			>
				<div class="flex w-full justify-between items-center">
					<div class="text-xs text-lightGray-100 dark:text-customGray-300">{$i18n.t('Change password')}</div>
				</div>
			</div>
			<div class="flex flex-col w-full mb-2.5">
				<div class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md">
					{#if currentPassword}
						<div class="text-xs absolute left-2.5 top-1 text-lightGray-100/50 dark:text-customGray-100/50">
							{$i18n.t('Current password')}
						</div>
					{/if}
					<input
						class={`px-2.5 text-sm ${currentPassword ? 'pt-2' : 'pt-0'} text-lightGray-100 placeholder:text-lightGray-100 w-full h-12 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none`}
						type="password"
						bind:value={currentPassword}
						placeholder={$i18n.t('Current password')}
						autocomplete="current-password"
						required
					/>
				</div>
			</div>

			<div class="flex flex-col w-full mb-2.5">
				<div class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md">
					{#if newPassword}
						<div class="text-xs absolute left-2.5 top-1 text-lightGray-100/50 dark:text-customGray-100/50">
							{$i18n.t('New password')}
						</div>
					{/if}
					<input
						class={`px-2.5 text-sm ${newPassword ? 'pt-2' : 'pt-0'} text-lightGray-100 placeholder:text-lightGray-100 w-full h-12 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none`}
						type="password"
						bind:value={newPassword}
						placeholder={$i18n.t('Enter your new password')}
						autocomplete="new-password"
						required
					/>
				</div>
			</div>

			<div class="flex flex-col w-full">
				<div class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md">
					{#if newPasswordConfirm}
						<div class="text-xs absolute left-2.5 top-1 text-lightGray-100/50 dark:text-customGray-100/50">
							{$i18n.t('Confirm password')}
						</div>
					{/if}
					<input
						class={`px-2.5 text-sm ${newPasswordConfirm ? 'pt-2' : 'pt-0'} text-lightGray-100 placeholder:text-lightGray-100 w-full h-12 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none`}
						type="password"
						bind:value={newPasswordConfirm}
						placeholder={$i18n.t('Confirm password')}
						autocomplete="off"
						required
					/>
				</div>
			</div>
			<!-- <UpdatePassword /> -->
		</div>

		<!-- <hr class=" dark:border-gray-850 my-4" /> -->

		<!-- <div class="flex justify-between items-center text-sm">
			<div class="  font-medium">{$i18n.t('API keys')}</div>
			<button
				class=" text-xs font-medium text-gray-500"
				type="button"
				on:click={() => {
					showAPIKeys = !showAPIKeys;
				}}>{showAPIKeys ? $i18n.t('Hide') : $i18n.t('Show')}</button
			>
		</div> -->

		<!-- {#if showAPIKeys}
			<div class="flex flex-col gap-4">
				<div class="justify-between w-full">
					<div class="flex justify-between w-full">
						<div class="self-center text-xs font-medium">{$i18n.t('JWT Token')}</div>
					</div>

					<div class="flex mt-2">
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
				{#if $config?.features?.enable_api_key ?? true}
					<div class="justify-between w-full">
						<div class="flex justify-between w-full">
							<div class="self-center text-xs font-medium">{$i18n.t('API Key')}</div>
						</div>
						<div class="flex mt-2">
							{#if APIKey}
								<SensitiveInput value={APIKey} readOnly={true} />

								<button
									class="ml-1.5 px-1.5 py-1 dark:hover:bg-gray-850 transition rounded-lg"
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
										class=" px-1.5 py-1 dark:hover:bg-gray-850transition rounded-lg"
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
									class="flex gap-1.5 items-center font-medium px-3.5 py-1.5 rounded-lg bg-gray-100/70 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-850 transition"
									on:click={() => {
										createAPIKeyHandler();
									}}
								>
									<Plus strokeWidth="2" className=" size-3.5" />

									{$i18n.t('Create new secret key')}</button
								>
							{/if}
						</div>
					</div>
				{/if}
			</div>
		{/if} -->
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class=" text-xs w-[168px] h-10 px-3 py-2 transition rounded-lg {loading
				? ' cursor-not-allowed bg-lightGray-300 hover:bg-lightGray-700 text-lightGray-100 dark:bg-customGray-950 dark:hover:bg-customGray-950 dark:text-white border border-lightGray-400 dark:border-customGray-700'
				: 'bg-lightGray-300 hover:bg-lightGray-700 text-lightGray-100 dark:bg-customGray-900 dark:hover:bg-customGray-950 dark:text-customGray-200 border border-lightGray-400 dark:border-customGray-700'} flex justify-center items-center"
			type="submit"
			disabled={loading}
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
	<div class="flex w-full justify-between items-center py-2.5 border-b border-lightGray-400 dark:border-customGray-700 mb-2">
		<div class="flex w-full justify-between items-center">
			<div class="text-xs dark:text-customGray-300">{$i18n.t('Delete account')}</div>
		</div>
	</div>
	<div class="flex justify-between items-start pt-3 pb-5">
		<button type="button" class="flex items-center text-xs text-[#F65351]" on:click={() => {
			showDeleteConfirm = true;
		}}>
			<DeleteIcon className="mr-1 size-4" />
			{$i18n.t('Delete account')}
		</button>
		<div class="shrink-0 w-[218px] dark:text-customGray-100/50 text-xs">
			{$i18n.t('This action is not reversible, so please continue with caution.')}
		</div>
	</div>
</div>
