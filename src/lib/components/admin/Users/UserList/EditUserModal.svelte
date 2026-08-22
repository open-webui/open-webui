<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import { createEventDispatcher } from 'svelte';
	import { onMount, getContext } from 'svelte';

	import { goto } from '$app/navigation';

	import {
		assignCustomRole,
		getCustomRoles,
		getUserGroupsById,
		unassignCustomRole,
		updateUserById
	} from '$lib/apis/users';

	import Modal from '$lib/components/common/Modal.svelte';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import XMark from '$lib/components/icons/XMark.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import UserProfileImage from '$lib/components/chat/Settings/Account/UserProfileImage.svelte';

	const i18n: any = getContext('i18n');
	const dispatch = createEventDispatcher();
	dayjs.extend(localizedFormat);

	export let show = false;
	export let selectedUser;
	export let sessionUser;

	let initializedUserId = '';
	$: if (show && selectedUser?.id && initializedUserId !== selectedUser.id) {
		initializedUserId = selectedUser.id;
		init();
	}
	$: if (!show) initializedUserId = '';

	const init = () => {
		if (selectedUser) {
			_user = { ...selectedUser };
			_user.password = '';
			loadUserGroups();
			loadCustomRoles();
		}
	};

	const loadCustomRoles = async () => {
		customRolesLoading = true;
		customRolesError = '';
		try {
			const response = await getCustomRoles(localStorage.token, true);
			customRoles = response?.items ?? [];
		} catch (error) {
			customRolesError = `${error}`;
			customRoles = [];
		} finally {
			customRolesLoading = false;
		}
	};

	const isCustomRole = (value: string) => value?.startsWith('custom:');
	const customRoleId = (value: string) => value?.slice('custom:'.length);
	const legacyRoles = new Set(['admin', 'user', 'pending']);
	const isActiveCustomRole = (value: string) =>
		isCustomRole(value) &&
		customRoles.some((customRole) => customRole.id === customRoleId(value) && customRole.active);

	let _user: any = {
		profile_image_url: '',
		role: 'pending',
		name: '',
		email: '',
		password: ''
	};

	let userGroups: any[] | null = null;
	let customRoles: any[] = [];
	let customRolesLoading = false;
	let customRolesError = '';

	const submitHandler = async () => {
		try {
			const { role, ...profileData } = _user;
			const currentRoleIsCustom = isCustomRole(selectedUser.role);
			const targetIsLegacy = legacyRoles.has(role);
			const targetIsActiveCustom = isActiveCustomRole(role);
			const roleChanged = role !== selectedUser.role;

			// Custom-role references are owned by the custom-role endpoints. Never
			// send a stale, inactive, unknown, or malformed reference to the legacy
			// user update endpoint during a profile-only save.
			if (targetIsLegacy && !currentRoleIsCustom) {
				await updateUserById(localStorage.token, selectedUser.id, _user as any);
			} else {
				await updateUserById(localStorage.token, selectedUser.id, profileData as any);
			}

			if (targetIsActiveCustom && roleChanged) {
				await assignCustomRole(localStorage.token, selectedUser.id, customRoleId(role));
			} else if (targetIsLegacy && currentRoleIsCustom) {
				await unassignCustomRole(
					localStorage.token,
					customRoleId(selectedUser.role),
					selectedUser.id
				);
				await updateUserById(localStorage.token, selectedUser.id, _user as any);
			}
			dispatch('save');
			show = false;
		} catch (error) {
			toast.error(`${error}`);
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
</script>

<Modal size="sm" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-4 pt-3 pb-1">
			<div class=" text-sm font-medium self-center">{$i18n.t('Edit User')}</div>
			<button
				class="self-center rounded-lg p-1 text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
				aria-label={$i18n.t('Close')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-4'} />
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
					<div class=" px-5 pt-3 pb-5 w-full">
						<div class="flex self-center w-full">
							<div class=" self-start h-full mr-6">
								<UserProfileImage
									imageClassName="size-14"
									bind:profileImageUrl={_user.profile_image_url}
									user={_user}
								/>
							</div>

							<div class=" flex-1 min-w-0">
								<div class="overflow-hidden w-ful mb-2">
									<div class=" self-center capitalize font-normal truncate">
										{selectedUser.name}
									</div>

									<div class="text-xs text-gray-500">
										{$i18n.t('Created at')}
										{dayjs(selectedUser.created_at * 1000).format('LL')}
									</div>
								</div>

								<div class=" flex flex-col space-y-1.5">
									{#if (userGroups ?? []).length > 0}
										<div class="flex flex-col w-full text-sm">
											<div class="mb-1 text-xs text-gray-500">{$i18n.t('User Groups')}</div>

											<div class="flex flex-wrap gap-1 my-0.5 -mx-1">
												{#each userGroups as userGroup}
													<span
														class="px-1.5 py-0.5 rounded-xl bg-gray-100 dark:bg-gray-850 text-xs"
													>
														<a
															href={'/admin/users/groups?id=' + userGroup.id}
															on:click|preventDefault={() =>
																goto('/admin/users/groups?id=' + userGroup.id)}
														>
															{userGroup.name}
														</a>
													</span>
												{/each}
											</div>
										</div>
									{/if}

									<div class="flex flex-col w-full">
										<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Role')}</div>

										<div class="flex-1">
											<select
												class="w-full text-sm bg-transparent disabled:text-gray-500 dark:disabled:text-gray-500 outline-hidden"
												bind:value={_user.role}
												aria-label={$i18n.t('Role')}
												disabled={_user.id == sessionUser?.id}
												required
											>
												<option value="admin">{$i18n.t('Admin')}</option>
												<option value="user">{$i18n.t('User')}</option>
												<option value="pending">{$i18n.t('Pending')}</option>
												{#if customRolesLoading}
													<option disabled>{$i18n.t('Loading custom roles…')}</option>
												{:else}
													{#each customRoles.filter((customRole) => customRole.active || customRole.id === customRoleId(_user.role)) as customRole}
														<option value={`custom:${customRole.id}`} disabled={!customRole.active}>
															{customRole.display_name}{customRole.active
																? ''
																: ` (${$i18n.t('Inactive')})`}
														</option>
													{/each}
													{#if isCustomRole(_user.role) && !customRoles.some((customRole) => customRole.id === customRoleId(_user.role))}
														<option value={_user.role}
															>{$i18n.t('Current custom role')} ({customRoleId(_user.role)})</option
														>
													{/if}
												{/if}
											</select>
											{#if customRolesError}
												<div class="mt-1 text-xs text-red-600 dark:text-red-400" role="alert">
													{$i18n.t('Custom roles could not be loaded')}: {customRolesError}
												</div>
											{/if}
										</div>
									</div>

									<div class="flex flex-col w-full">
										<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Name')}</div>

										<div class="flex-1">
											<input
												class="w-full text-sm bg-transparent outline-hidden"
												type="text"
												bind:value={_user.name}
												aria-label={$i18n.t('Name')}
												placeholder={$i18n.t('Enter Your Name')}
												autocomplete="off"
												required
											/>
										</div>
									</div>

									<div class="flex flex-col w-full">
										<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Email')}</div>

										<div class="flex-1">
											<input
												class="w-full text-sm bg-transparent disabled:text-gray-500 dark:disabled:text-gray-500 outline-hidden"
												type="email"
												bind:value={_user.email}
												aria-label={$i18n.t('Email')}
												placeholder={$i18n.t('Enter Your Email')}
												autocomplete="off"
												required
											/>
										</div>
									</div>

									{#if _user?.oauth}
										<div class="flex flex-col w-full">
											<div class=" mb-1 text-xs text-gray-500">{$i18n.t('OAuth ID')}</div>

											<div class="flex-1 text-sm break-all mb-1 flex flex-col space-y-1">
												{#each Object.keys(_user.oauth) as key}
													<div>
														<span class="text-gray-500">{key}</span>
														<span class="">{_user.oauth[key]?.sub}</span>
													</div>
												{/each}
											</div>
										</div>
									{/if}

									<div class="flex flex-col w-full">
										<label for="edit-user-password" class="mb-1 text-xs text-gray-500"
											>{$i18n.t('New Password')}</label
										>

										<div class="flex-1">
											<SensitiveInput
												id="edit-user-password"
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
							</div>
						</div>

						<div class="flex justify-end pt-3 text-sm font-normal">
							<button
								class="px-3.5 py-1.5 text-sm font-normal bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center"
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
