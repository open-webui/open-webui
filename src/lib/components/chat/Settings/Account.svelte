<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';

	import { user } from '$lib/stores';
	import { updateUserProfile, createAPIKey, getAPIKey } from '$lib/apis/auths';

	import UpdatePassword from './Account/UpdatePassword.svelte';
	import { getGravatarUrl } from '$lib/apis/utils';
	import { generateInitialsImage, canvasPixelTest } from '$lib/utils';
	import { copyToClipboard } from '$lib/utils';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let profileImageUrl = '';
	let name = '';

	let showAPIKeys = false;

	let JWTTokenCopied = false;

	let APIKey = '';
	let APIKeyCopied = false;

	let profileImageInputElement: HTMLInputElement;

	const submitHandler = async () => {
		if (name !== $user.name) {
			if (profileImageUrl === generateInitialsImage($user.name) || profileImageUrl === '') {
				profileImageUrl = generateInitialsImage(name);
			}
		}

		const updatedUser = await updateUserProfile(localStorage.token, name, profileImageUrl).catch(
			(error) => {
				toast.error(error);
			}
		);

		if (updatedUser) {
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

	onMount(async () => {
		name = $user.name;
		profileImageUrl = $user.profile_image_url;

		APIKey = await getAPIKey(localStorage.token).catch((error) => {
			console.log(error);
			return '';
		});
	});
</script>

<div class="flex flex-col h-full justify-between text-sm">
	<div class=" space-y-3 pr-1.5 overflow-y-scroll max-h-[25rem]">
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
								const url = await getGravatarUrl($user.email);

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
							class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
							type="text"
							bind:value={name}
							required
						/>
					</div>
				</div>
			</div>
		</div>

		<div class="py-0.5">
			<UpdatePassword />
		</div>

		<hr class=" dark:border-gray-850 my-4" />

		<div class="flex justify-between items-center text-sm">
			<div class="  font-medium">{$i18n.t('API keys')}</div>
			<button
				class=" text-xs font-medium text-gray-500"
				type="button"
				on:click={() => {
					showAPIKeys = !showAPIKeys;
				}}>{showAPIKeys ? $i18n.t('Hide') : $i18n.t('Show')}</button
			>
		</div>

		{#if showAPIKeys}
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
			</div>
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
