<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';

	import { user } from '$lib/stores';
	import { updateUserProfile } from '$lib/apis/auths';

	import UpdatePassword from './Account/UpdatePassword.svelte';
	import { getGravatarUrl } from '$lib/apis/utils';
	import { copyToClipboard } from '$lib/utils';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let profileImageUrl = '';
	let name = '';
	let showJWTToken = false;
	let JWTTokenCopied = false;
	let profileImageInputElement: HTMLInputElement;

	const submitHandler = async () => {
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

	onMount(() => {
		name = $user.name;
		profileImageUrl = $user.profile_image_url;
	});
</script>

<div class="flex flex-col h-full justify-between text-sm">
	<div class=" space-y-3 pr-1.5 overflow-y-scroll max-h-[22rem]">
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

						// Calculate the new width and height to fit within 100x100
						let newWidth, newHeight;
						if (aspectRatio > 1) {
							newWidth = 100 * aspectRatio;
							newHeight = 100;
						} else {
							newWidth = 100;
							newHeight = 100 / aspectRatio;
						}

						// Set the canvas size
						canvas.width = 100;
						canvas.height = 100;

						// Calculate the position to center the image
						const offsetX = (100 - newWidth) / 2;
						const offsetY = (100 - newHeight) / 2;

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
					['image/gif', 'image/jpeg', 'image/png'].includes(files[0]['type'])
				) {
					reader.readAsDataURL(files[0]);
				}
			}}
		/>

		<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Profile')}</div>

		<div class="flex space-x-5">
			<div class="flex flex-col">
				<div class="self-center">
					<button
						class="relative rounded-full dark:bg-gray-700"
						type="button"
						on:click={() => {
							profileImageInputElement.click();
						}}
					>
						<img
							src={profileImageUrl !== '' ? profileImageUrl : '/user.png'}
							alt="profile"
							class=" rounded-full w-16 h-16 object-cover"
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
				<button
					class=" text-xs text-gray-600"
					on:click={async () => {
						const url = await getGravatarUrl($user.email);

						profileImageUrl = url;
					}}>{$i18n.t('Use Gravatar')}</button
				>
			</div>

			<div class="flex-1">
				<div class="flex flex-col w-full">
					<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Name')}</div>

					<div class="flex-1">
						<input
							class="w-full rounded py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none"
							type="text"
							bind:value={name}
							required
						/>
					</div>
				</div>
			</div>
		</div>

		<hr class=" dark:border-gray-700 my-4" />
		<UpdatePassword />

		<hr class=" dark:border-gray-700 my-4" />

		<div class=" w-full justify-between">
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs font-medium">{$i18n.t('JWT Token')}</div>
			</div>

			<div class="flex mt-2">
				<div class="flex w-full">
					<input
						class="w-full rounded-l-lg py-1.5 pl-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none"
						type={showJWTToken ? 'text' : 'password'}
						value={localStorage.token}
						disabled
					/>

					<button
						class="dark:bg-gray-800 px-2 transition rounded-r-lg"
						on:click={() => {
							showJWTToken = !showJWTToken;
						}}
					>
						{#if showJWTToken}
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								class="w-4 h-4"
							>
								<path
									fill-rule="evenodd"
									d="M3.28 2.22a.75.75 0 0 0-1.06 1.06l10.5 10.5a.75.75 0 1 0 1.06-1.06l-1.322-1.323a7.012 7.012 0 0 0 2.16-3.11.87.87 0 0 0 0-.567A7.003 7.003 0 0 0 4.82 3.76l-1.54-1.54Zm3.196 3.195 1.135 1.136A1.502 1.502 0 0 1 9.45 8.389l1.136 1.135a3 3 0 0 0-4.109-4.109Z"
									clip-rule="evenodd"
								/>
								<path
									d="m7.812 10.994 1.816 1.816A7.003 7.003 0 0 1 1.38 8.28a.87.87 0 0 1 0-.566 6.985 6.985 0 0 1 1.113-2.039l2.513 2.513a3 3 0 0 0 2.806 2.806Z"
								/>
							</svg>
						{:else}
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								class="w-4 h-4"
							>
								<path d="M8 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z" />
								<path
									fill-rule="evenodd"
									d="M1.38 8.28a.87.87 0 0 1 0-.566 7.003 7.003 0 0 1 13.238.006.87.87 0 0 1 0 .566A7.003 7.003 0 0 1 1.379 8.28ZM11 8a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
									clip-rule="evenodd"
								/>
							</svg>
						{/if}
					</button>
				</div>

				<button
					class="ml-1.5 px-1.5 py-1 hover:bg-gray-800 transition rounded-lg"
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
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="  px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
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
