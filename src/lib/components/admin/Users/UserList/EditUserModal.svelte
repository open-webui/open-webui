<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import { createEventDispatcher } from 'svelte';
	import { onMount, getContext } from 'svelte';

	import { goto } from '$app/navigation';

	import {
		updateUserById,
		getUserGroupsById,
		revokeUserSessions,
		getUserAPIKeyById,
		createUserAPIKeyById,
		deleteUserAPIKeyById
	} from '$lib/apis/users';
	import { copyToClipboard } from '$lib/utils';
	import { config } from '$lib/stores';

	import Modal from '$lib/components/common/Modal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	let showRevokeConfirmation = false;
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import Clipboard from '$lib/components/icons/Clipboard.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Refresh from '$lib/components/icons/Refresh.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import UserProfileImage from '$lib/components/chat/Settings/Account/UserProfileImage.svelte';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');
	const dispatch = createEventDispatcher();
	dayjs.extend(localizedFormat);

	export let show = false;
	export let selectedUser;
	export let sessionUser;

	$: if (show) {
		init();
	}

	const init = () => {
		if (selectedUser) {
			_user = { ...selectedUser, password: '' };
			loadUserGroups();
			loadAPIKey();
		}
	};

	let _user = {
		profile_image_url: '',
		role: 'pending',
		name: '',
		email: '',
		password: ''
	};

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

	const loadUserGroups = async () => {
		if (!selectedUser?.id) return;
		userGroups = null;

		userGroups = await getUserGroupsById(localStorage.token, selectedUser.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
	};

	let canManageAPIKey = false;
	let APIKey = '';
	let APIKeyCopied = false;
	let showAPIKeyMenu = false;
	let showDeleteAPIKeyConfirm = false;

	const loadAPIKey = async () => {
		canManageAPIKey = false;
		APIKey = '';

		if (!($config?.features?.enable_api_keys ?? true)) return;

		const userId = selectedUser.id;
		// undefined means refused for this user, null means no key yet
		const key = await getUserAPIKeyById(localStorage.token, userId).catch(() => undefined);
		if (key === undefined || userId !== selectedUser.id) return;

		APIKey = key ?? '';
		canManageAPIKey = true;
	};

	const createAPIKeyHandler = async () => {
		const key = await createUserAPIKeyById(localStorage.token, selectedUser.id).catch((error) => {
			toast.error(error.message);
			return null;
		});

		if (key) {
			APIKey = key;
			toast.success($i18n.t('API Key created.'));
		}
	};

	const deleteAPIKeyHandler = async () => {
		const res = await deleteUserAPIKeyById(localStorage.token, selectedUser.id).catch((error) => {
			toast.error(error.message);
			return false;
		});

		if (res) {
			APIKey = '';
			toast.success($i18n.t('API Key deleted.'));
		}
	};
</script>

<ConfirmDialog
	bind:show={showRevokeConfirmation}
	title={$i18n.t('Sign out all devices?')}
	message={$i18n.t('This user will need to sign in again on every device. API keys remain active.')}
	on:confirm={async () => {
		try {
			await revokeUserSessions(localStorage.token, selectedUser.id);
			toast.success($i18n.t('All sessions revoked'));
		} catch (error) {
			toast.error(error instanceof Error ? error.message : String(error));
		}
	}}
/>

<ConfirmDialog
	bind:show={showDeleteAPIKeyConfirm}
	title={$i18n.t('Delete API Key?')}
	message={$i18n.t('This will revoke the current API key.')}
	confirmLabel={$i18n.t('Delete')}
	on:confirm={deleteAPIKeyHandler}
/>

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
										{dayjs(selectedUser.created_at * 1000)
											.locale($i18n.language)
											.format('LL')}
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
										<div class=" mb-1 text-xs text-gray-500">{$i18n.t('New Password')}</div>

										<div class="flex-1">
											<SensitiveInput
												class="w-full text-sm bg-transparent outline-hidden"
												type="password"
												aria-label={$i18n.t('New Password')}
												placeholder={$i18n.t('Enter New Password')}
												bind:value={_user.password}
												autocomplete="new-password"
												required={false}
											/>
										</div>
									</div>

									{#if canManageAPIKey}
										<div class="flex flex-col w-full">
											<div class=" mb-1 text-xs text-gray-500">{$i18n.t('API Key')}</div>

											<div class="flex flex-1 items-center">
												{#if APIKey}
													<SensitiveInput
														variant="settings"
														outerClassName="flex flex-1 min-w-0"
														value={APIKey}
														placeholder={$i18n.t('API Key')}
														readOnly={true}
													/>

													<button
														type="button"
														class="ml-1.5 rounded-sm px-1.5 py-1 text-gray-500 transition hover:text-gray-700 dark:hover:text-gray-300"
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
															<Check className="size-4" />
														{:else}
															<Clipboard className="size-4" />
														{/if}
													</button>

													<Dropdown bind:show={showAPIKeyMenu} align="end" sideOffset={4}>
														<Tooltip content={$i18n.t('More')}>
															<button
																type="button"
																class="rounded-sm px-1.5 py-1 text-gray-500 transition hover:text-gray-700 dark:hover:text-gray-300"
																aria-label={$i18n.t('More')}
															>
																<EllipsisHorizontal strokeWidth="2" className="size-4" />
															</button>
														</Tooltip>

														<div slot="content">
															<DropdownMenu className="min-w-[10.625rem]">
																<button
																	type="button"
																	on:click={() => {
																		showAPIKeyMenu = false;
																		createAPIKeyHandler();
																	}}
																>
																	<Refresh strokeWidth="2" className="size-3.5 scale-90" />
																	<div class="flex items-center">{$i18n.t('Create new key')}</div>
																</button>

																<hr class="border-gray-50 dark:border-gray-850/30" />

																<button
																	type="button"
																	on:click={() => {
																		showAPIKeyMenu = false;
																		showDeleteAPIKeyConfirm = true;
																	}}
																>
																	<XMark strokeWidth="2" className="size-3.5" />
																	<div class="flex items-center">{$i18n.t('Delete')}</div>
																</button>
															</DropdownMenu>
														</div>
													</Dropdown>
												{:else}
													<button
														type="button"
														class="inline-flex items-center gap-1.5 text-sm text-gray-500 transition-colors hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
														on:click={createAPIKeyHandler}
													>
														<Plus strokeWidth="2" className="size-3.5" />
														{$i18n.t('settings.personal.account.createNewSecretKey.label')}
													</button>
												{/if}
											</div>
										</div>
									{/if}
								</div>
							</div>
						</div>

						<div class="flex justify-between pt-3 text-sm font-normal">
							<button
								type="button"
								class="text-sm text-gray-500 transition-colors hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
								on:click={() => {
									showRevokeConfirmation = true;
								}}>{$i18n.t('Sign out all devices')}</button
							>
							<button
								class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-gray-900 px-2.5 text-xs font-normal text-white transition hover:bg-black disabled:opacity-60 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white"
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
