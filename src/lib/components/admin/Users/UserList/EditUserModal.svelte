<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import { createEventDispatcher } from 'svelte';
	import { onMount, getContext } from 'svelte';

	import { goto } from '$app/navigation';

	import { updateUserById, getUserGroupsById } from '$lib/apis/users';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { getGravatarUrl } from '$lib/apis/utils';
	import { generateInitialsImage, canvasPixelTest } from '$lib/utils';

	import Modal from '$lib/components/common/Modal.svelte';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import XMark from '$lib/components/icons/XMark.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();
	dayjs.extend(localizedFormat);

	export let show = false;
	export let selectedUser;
	export let sessionUser;

	let _user = {
		profile_image_url: '',
		role: 'pending',
		name: '',
		email: '',
		password: ''
	};

	let userGroups: any[] | null = null;
	let profileImageInputElement: HTMLInputElement;

	const submitHandler = async () => {
		const res = await updateUserById(localStorage.token, selectedUser.id, _user).catch((error) => {
			toast.error(`${error}`);
		});

		if (res) {
			dispatch('save');
			show = false;
		}
	};

	const loadUserGroups = async () => {
		if (!selectedUser?.id) return;
		userGroups = null;

		userGroups = await getUserGroupsById(localStorage.token, selectedUser.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
	};

	onMount(() => {
		if (selectedUser) {
			_user = selectedUser;
			_user.password = '';
			loadUserGroups();
		}
	});
</script>

<!-- Changed size from "sm" to "md" for larger modal, removed id prop that was causing warnings -->
<Modal size="md" bind:show>
	<input
		id="profile-image-input-admin"
		bind:this={profileImageInputElement}
		type="file"
		hidden
		accept="image/*"
		on:change={() => {
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
					_user.profile_image_url = compressedSrc;

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
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-2">
			<div class=" text-lg font-medium self-center">{$i18n.t('Edit User')}</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div class=" flex items-center rounded-md px-5 py-2 w-full">
						<div class="flex flex-col self-start group mr-5">
							<div class="self-center flex">
								<button
									class="relative rounded-full dark:bg-gray-700"
									type="button"
									on:click={() => {
										profileImageInputElement.click();
									}}
								>
									<img
										src={_user.profile_image_url !== ''
											? _user.profile_image_url
											: generateInitialsImage(_user.name)}
										alt="profile"
										class="rounded-full size-14 md:size-14 object-cover"
									/>

									<div class="absolute bottom-0 right-0 opacity-0 group-hover:opacity-100 transition">
										<div class="p-1 rounded-full bg-white text-black border-gray-100 shadow">
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 20 20"
												fill="currentColor"
												class="size-3"
											>
												<path
													d="m2.695 14.762-1.262 3.155a.5.5 0 0 0 .65.65l3.155-1.262a4 4 0 0 0 1.343-.886L17.5 5.501a2.121 2.121 0 0 0-3-3L3.58 13.419a4 4 0 0 0-.885 1.343Z"
												/>
											</svg>
										</div>
									</div>
								</button>
							</div>
							<div class="flex flex-col w-full justify-center mt-1">
								<button
									class=" text-xs text-center text-gray-500 rounded-lg py-0.5 opacity-0 group-hover:opacity-100 transition-all"
									on:click={async () => {
										_user.profile_image_url = `${WEBUI_BASE_URL}/user.png`;
									}}>{$i18n.t('Remove')}</button
								>

								<button
									class=" text-xs text-center text-gray-800 dark:text-gray-400 rounded-lg py-0.5 opacity-0 group-hover:opacity-100 transition-all"
									on:click={async () => {
										if (canvasPixelTest()) {
											_user.profile_image_url = generateInitialsImage(_user.name);
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
									}}>{$i18n.t('Initials')}</button
								>

								<button
									class=" text-xs text-center text-gray-800 dark:text-gray-400 rounded-lg py-0.5 opacity-0 group-hover:opacity-100 transition-all"
									on:click={async () => {
										const url = await getGravatarUrl(localStorage.token, _user?.email);

										_user.profile_image_url = url;
									}}>{$i18n.t('Gravatar')}</button
								>
							</div>
						</div>

						<div class="overflow-hidden w-full">
							<div class=" self-center capitalize font-semibold truncate">{selectedUser.name}</div>

							<div class="text-xs text-gray-500">
								{$i18n.t('Created at')}
								{dayjs(selectedUser.created_at * 1000).format('LL')}
							</div>
							<div class="text-xs text-gray-500">
								{$i18n.t('Last active at')}
								{dayjs(selectedUser.last_active_at * 1000).fromNow()}
							</div>
							{#if selectedUser.oauth_sub}
								<div class="text-xs text-gray-500">
									{$i18n.t('OAuth ID')}
									{selectedUser.oauth_sub}
								</div>
							{/if}

							{#if userGroups}
								<div class="flex flex-wrap gap-1 my-0.5 -mx-1">
									{#each userGroups as userGroup}
										<span
											class="px-2 py-0.5 rounded-full bg-green-500/20 text-green-700 dark:text-green-200 text-xs"
										>
											<a
												href={'/admin/users/groups?id=' + userGroup.id}
												on:click|preventDefault={() => goto('/admin/users/groups?id=' + userGroup.id)}
											>
												{userGroup.name}
											</a>
										</span>
									{/each}
								</div>
							{/if}
						</div>
					</div>

					<div class=" px-5 pt-3 pb-5">
						<div class=" flex flex-col space-y-1.5">
							<div class="flex flex-col w-full">
								<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Change Role')}</div>

								<div class="flex-1">
									<select
										class="w-full dark:bg-gray-900 text-sm bg-transparent disabled:text-gray-500 dark:disabled:text-gray-500 outline-hidden"
										bind:value={_user.role}
										disabled={_user.id == sessionUser.id}
										required
									>
										<option value="admin">{$i18n.t('Admin')}</option>
										<option value="user">{$i18n.t('User')}</option>
										<option value="pending">{$i18n.t('Pending')}</option>
									</select>
								</div>
							</div>

							<div class="flex flex-col w-full">
								<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Change Email')}</div>

								<div class="flex-1">
									<input
										class="w-full text-sm bg-transparent disabled:text-gray-500 dark:disabled:text-gray-500 outline-hidden"
										type="email"
										bind:value={_user.email}
										placeholder={$i18n.t('Enter Your Email')}
										autocomplete="off"
										required
									/>
								</div>
							</div>

							<div class="flex flex-col w-full">
								<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Change Name')}</div>

								<div class="flex-1">
									<input
										class="w-full text-sm bg-transparent outline-hidden"
										type="text"
										bind:value={_user.name}
										placeholder={$i18n.t('Enter Your Name')}
										autocomplete="off"
										required
									/>
								</div>
							</div>

							<div class="flex flex-col w-full">
								<div class=" mb-1 text-xs text-gray-500">{$i18n.t('New Password')}</div>

								<div class="flex-1">
									<!-- Removed class and autocomplete props that were causing warnings -->
									<!-- Applied styling directly with style attribute if needed, or wrap in a div -->
									<div class="w-full">
										<SensitiveInput
											type="password"
											placeholder={$i18n.t('Enter New Password')}
											bind:value={_user.password}
											required={false}
										/>
									</div>
								</div>
							</div>
						</div>

						<div class="flex justify-end pt-3 text-sm font-medium">
							<button
								class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center"
								type="submit"
							>
								{$i18n.t('Save')}
							</button>
						</div>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>

<style>
	input::-webkit-outer-spin-button,
	input::-webkit-inner-spin-button {
		/* display: none; <- Crashes Chrome on hover */
		-webkit-appearance: none;
		margin: 0; /* <-- Apparently some margin are still there even though it's hidden */
	}

	.tabs::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.tabs {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
	}

	input[type='number'] {
		-moz-appearance: textfield; /* Firefox */
	}

	/* Add custom styling for SensitiveInput if needed */
	:global(.sensitive-input) {
		width: 100%;
		font-size: 0.875rem;
		background: transparent;
		outline: none;
	}
</style>
