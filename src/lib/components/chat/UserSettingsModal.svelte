<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { settings, user } from '$lib/stores';
	import { updateUserProfile, getSessionUser } from '$lib/apis/auths';

	import Modal from '../common/Modal.svelte';
	import About from './Settings/About.svelte';
	import XMark from '../icons/XMark.svelte';
	import UserCircle from '../icons/UserCircle.svelte';
	import InfoCircle from '../icons/InfoCircle.svelte';
	import UserProfileImage from './Settings/Account/UserProfileImage.svelte';
	import Textarea from '../common/Textarea.svelte';

	const i18n = getContext('i18n');

	export let show = false;

	let selectedTab = 'account';

	let profileImageUrl = '';
	let bio = '';
	let loaded = false;

	$: if (show && !loaded) {
		loadUserData();
	}

	async function loadUserData() {
		const userData = await getSessionUser(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (userData) {
			profileImageUrl = userData?.profile_image_url ?? '';
			bio = userData?.bio ?? '';
		}

		loaded = true;
	}

	const submitHandler = async () => {
		const updatedUser = await updateUserProfile(localStorage.token, {
			profile_image_url: profileImageUrl,
			bio: bio ? bio : null,
			name: $user?.name ?? '',
			body: $user?.body ?? ''
		}).catch((error) => {
			toast.error(`${error}`);
		});

		if (updatedUser) {
			const sessionUser = await getSessionUser(localStorage.token).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			await user.set(sessionUser);
			toast.success($i18n.t('Settings saved successfully!'));
			return true;
		}
		return false;
	};
</script>

<Modal size="md" bind:show>
	<div class="text-gray-700 dark:text-gray-100 mx-1">
		<div class="flex justify-between dark:text-gray-300 px-4 md:px-4.5 pt-4.5 pb-0.5 md:pb-2.5">
			<div class="text-lg font-medium self-center">{$i18n.t('Settings')}</div>
			<button
				aria-label={$i18n.t('Close settings modal')}
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className="w-5 h-5" />
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full pt-1 pb-4">
			<!-- Tabs -->
			<div
				role="tablist"
				class="tabs flex flex-row overflow-x-auto gap-2.5 mx-3 md:pr-4 md:gap-1 md:flex-col flex-1 md:flex-none md:w-40 dark:text-gray-200 text-sm text-left mb-1 md:mb-0"
			>
				<button
					role="tab"
					aria-controls="tab-account"
					aria-selected={selectedTab === 'account'}
					class={`px-0.5 md:px-2.5 py-1 min-w-fit rounded-xl flex-1 md:flex-none flex text-left transition
					${
						selectedTab === 'account'
							? ($settings?.highContrastMode ?? false)
								? 'dark:bg-gray-800 bg-gray-200'
								: ''
							: ($settings?.highContrastMode ?? false)
								? 'hover:bg-gray-200 dark:hover:bg-gray-800'
								: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'
					}`}
					on:click={() => {
						selectedTab = 'account';
					}}
				>
					<div class="self-center mr-2">
						<UserCircle strokeWidth="2" />
					</div>
					<div class="self-center">{$i18n.t('Account')}</div>
				</button>

				<button
					role="tab"
					aria-controls="tab-about"
					aria-selected={selectedTab === 'about'}
					class={`px-0.5 md:px-2.5 py-1 min-w-fit rounded-xl flex-1 md:flex-none flex text-left transition
					${
						selectedTab === 'about'
							? ($settings?.highContrastMode ?? false)
								? 'dark:bg-gray-800 bg-gray-200'
								: ''
							: ($settings?.highContrastMode ?? false)
								? 'hover:bg-gray-200 dark:hover:bg-gray-800'
								: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'
					}`}
					on:click={() => {
						selectedTab = 'about';
					}}
				>
					<div class="self-center mr-2">
						<InfoCircle strokeWidth="2" />
					</div>
					<div class="self-center">{$i18n.t('About')}</div>
				</button>
			</div>

			<!-- Content -->
			<div class="flex-1 px-3.5 md:pl-0 md:pr-4.5 md:min-h-[20rem] max-h-[28rem]">
				{#if selectedTab === 'account'}
					<div id="tab-account" class="flex flex-col h-full justify-between text-sm">
						<div class="overflow-y-scroll max-h-[24rem] md:max-h-full">
							<div class="space-y-1">
								<div>
									<div class="text-base font-medium">{$i18n.t('Your Account')}</div>
									<div class="text-xs text-gray-500 mt-0.5">
										{$i18n.t('Manage your profile information.')}
									</div>
								</div>

								<div class="flex space-x-5 my-4">
									<UserProfileImage bind:profileImageUrl user={$user} />

									<div class="flex flex-1 flex-col">
										<div class="flex-1">
											<div class="flex flex-col w-full">
												<div class="mb-1 text-xs font-medium">{$i18n.t('Bio')}</div>
												<div class="flex-1">
													<Textarea
														className="w-full text-sm dark:text-gray-300 bg-transparent outline-hidden"
														minSize={80}
														bind:value={bio}
														placeholder={$i18n.t('Share your background and interests')}
													/>
												</div>
											</div>
										</div>
									</div>
								</div>
							</div>
						</div>

						<div class="flex justify-end pt-3 text-sm font-medium">
							<button
								class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
								on:click={async () => {
									await submitHandler();
								}}
							>
								{$i18n.t('Save')}
							</button>
						</div>
					</div>
				{:else if selectedTab === 'about'}
					<About />
				{/if}
			</div>
		</div>
	</div>
</Modal>

<style>
	.tabs::-webkit-scrollbar {
		display: none;
	}

	.tabs {
		-ms-overflow-style: none;
		scrollbar-width: none;
	}
</style>
