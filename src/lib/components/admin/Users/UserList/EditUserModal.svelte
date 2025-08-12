<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import { createEventDispatcher } from 'svelte';
	import { onMount, getContext } from 'svelte';

	import { updateUserById, getUserGroupsById } from '$lib/apis/users';

	import { adminDisableUserTotp } from '$lib/apis/auths';

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

	let disablingTotp = false;
	let userGroups: any[] | null = null;

	const submitHandler = async () => {
		const res = await updateUserById(localStorage.token, selectedUser.id, _user).catch((error) => {
			toast.error(`${error}`);
		});

		if (res) {
			dispatch('save');
			show = false;
		}
	};

	const disableTotpHandler = async () => {
		if (!confirm($i18n.t('Are you sure you want to disable 2FA for this user? This will remove their TOTP setup and backup codes.'))) {
			return;
		}

		disablingTotp = true;
		
		try {
			await adminDisableUserTotp(localStorage.token, selectedUser.id);
			toast.success($i18n.t('2FA has been disabled for the user'));
			
			// Update the local user object to reflect the change
			selectedUser.totp_enabled = false;
			_user.totp_enabled = false;
			
			dispatch('save');
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			disablingTotp = false;
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

<Modal size="sm" bind:show>
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
						<div class=" self-center mr-5">
							<img
								src={selectedUser.profile_image_url}
								class=" max-w-[55px] object-cover rounded-full"
								alt="User profile"
							/>
						</div>

						<div>
							<div class=" self-center capitalize font-semibold">{selectedUser.name}</div>

							<div class="text-xs text-gray-500">
								{$i18n.t('Created at')}
								{dayjs(selectedUser.created_at * 1000).format('LL')}
							</div>
						</div>
					</div>

					<div class=" px-5 pt-3 pb-5">
						<div class=" flex flex-col space-y-1.5">
							<div class="flex flex-col w-full">
								<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Role')}</div>

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

							{#if userGroups}
								<div class="flex flex-col w-full text-sm">
									<div class="mb-1 text-xs text-gray-500">{$i18n.t('User Groups')}</div>

									{#if userGroups.length}
										<div class="flex flex-wrap gap-1 my-0.5 -mx-1">
											{#each userGroups as userGroup}
												<span class="px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-850 text-xs">
													{userGroup.name}
												</span>
											{/each}
										</div>
									{:else}
										<span>-</span>
									{/if}
								</div>
							{/if}

							<div class="flex flex-col w-full">
								<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Email')}</div>

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
								<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Name')}</div>

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
									<SensitiveInput
										class="w-full text-sm bg-transparent outline-hidden"
										type="password"
										placeholder={$i18n.t('Enter New Password')}
										bind:value={_user.password}
										autocomplete="new-password"
										required={false}
									/>
								</div>
							</div>
						</div>

						{#if selectedUser.totp_enabled}
							<div class="flex flex-col w-full">
								<div class="mb-1 text-xs text-gray-500">{$i18n.t('Two-Factor Authentication')}</div>
								
								<div class="flex items-center justify-between">
									<div class="flex items-center space-x-2">
										<div class="text-sm text-green-600 dark:text-green-400">
											{$i18n.t('Enabled')}
										</div>
										<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
										</svg>
									</div>
									
									<button
										type="button"
										class="px-3 py-1.5 text-xs font-medium text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/20 transition rounded-md flex items-center space-x-1"
										disabled={disablingTotp}
										on:click={disableTotpHandler}
									>
										{#if disablingTotp}
											<div class="animate-spin rounded-full h-3 w-3 border-b-2 border-red-600"></div>
										{:else}
											<svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
											</svg>
										{/if}
										<span>{$i18n.t('Disable')}</span>
									</button>
								</div>
							</div>
						{/if}

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
</style>
