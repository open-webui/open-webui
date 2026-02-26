<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import { createEventDispatcher } from 'svelte';
	import { onMount, getContext } from 'svelte';

	import { goto } from '$app/navigation';

	import {
		updateUserById,
		getUserGroupsById,
		forceGmailSync,
		getUserSpendLimits,
		updateUserSpendLimits,
		type SpendLimitsResponse
	} from '$lib/apis/users';

	import Modal from '$lib/components/common/Modal.svelte';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import XMark from '$lib/components/icons/XMark.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import UserProfileImage from '$lib/components/chat/Settings/Account/UserProfileImage.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();
	dayjs.extend(localizedFormat);

	export let show = false;
	export let selectedUser;
	export let sessionUser;

	// Spend limits state
	let spendLimits: SpendLimitsResponse | null = null;
	let spendLimitEnabled = false;
	let spendLimitDaily: string = '';
	let spendLimitMonthly: string = '';

	$: if (show) {
		init();
	}

	const init = () => {
		if (selectedUser) {
			_user = selectedUser;
			_user.password = '';
			loadUserGroups();
			loadSpendLimits();
		}
	};

	const loadSpendLimits = async () => {
		if (!selectedUser?.id) return;
		spendLimits = null;

		try {
			spendLimits = await getUserSpendLimits(localStorage.token, selectedUser.id);
			if (spendLimits) {
				spendLimitEnabled = spendLimits.spend_limit_enabled;
				spendLimitDaily = spendLimits.spend_limit_daily?.toString() ?? '';
				spendLimitMonthly = spendLimits.spend_limit_monthly?.toString() ?? '';
			}
		} catch (error) {
			console.error('Failed to load spend limits:', error);
		}
	};

	const saveSpendLimits = async (): Promise<boolean> => {
		if (!selectedUser?.id) return true;

		try {
			const res = await updateUserSpendLimits(localStorage.token, selectedUser.id, {
				spend_limit_enabled: spendLimitEnabled,
				spend_limit_daily: spendLimitDaily ? parseFloat(spendLimitDaily) : null,
				spend_limit_monthly: spendLimitMonthly ? parseFloat(spendLimitMonthly) : null
			});

			return !!res;
		} catch (error) {
			toast.error($i18n.t('Failed to update spend limits: {{error}}', { error }));
			return false;
		}
	};

	let _user = {
		profile_image_url: '',
		role: 'pending',
		name: '',
		email: '',
		password: '',
		gmail_sync_enabled: 0
	};

	let userGroups: any[] | null = null;

	const submitHandler = async () => {
		// Save user profile
		const res = await updateUserById(localStorage.token, selectedUser.id, _user).catch((error) => {
			toast.error(`${error}`);
		});

		if (!res) return;

		// Save spend limits if they've been loaded
		if (spendLimits !== null) {
			const limitsRes = await saveSpendLimits();
			if (!limitsRes) return;
		}

		dispatch('save');
		show = false;
	};

	const handleForceGmailSync = async () => {
		if (!selectedUser?.id) return;
		
		toast.info('Starting full Gmail sync...');
		
		try {
			const res = await forceGmailSync(localStorage.token, selectedUser.id);
			if (res) {
				toast.success('Gmail sync started! This may take a few minutes.');
			} else {
				toast.error('Failed to start Gmail sync');
			}
		} catch (error) {
			toast.error(`Gmail sync error: ${error}`);
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
			console.log('Selected user data:', selectedUser);
			_user = selectedUser;
			_user.password = '';
			// Ensure gmail_sync_enabled is properly set (default to 0 if undefined)
			_user.gmail_sync_enabled = _user.gmail_sync_enabled || 0;
			console.log('Processed user data:', _user);
			console.log('Gmail sync enabled value:', _user.gmail_sync_enabled);
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
				aria-label={$i18n.t('Close')}
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
					<div class=" px-5 pt-3 pb-5 w-full">
						<div class="flex self-center w-full">
							<div class=" self-start h-full mr-6">
								<UserProfileImage
									imageClassName="size-14"
									bind:profileImageUrl={_user.profile_image_url}
									user={_user}
								/>
							</div>

							<div class=" flex-1">
								<div class="overflow-hidden w-ful mb-2">
									<div class=" self-center capitalize font-medium truncate">
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

									<div class="flex flex-col w-full">
										<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Gmail Email Sync')}</div>

										<div class="flex-1 flex items-center space-x-2">
											<label class="relative inline-flex items-center cursor-pointer">
												<input
													type="checkbox"
													class="sr-only peer"
													checked={_user.gmail_sync_enabled === 1}
													on:change={(e) => {
														_user.gmail_sync_enabled = e.target.checked ? 1 : 0;
													}}
												/>
												<div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-gray-300 dark:peer-focus:ring-gray-600 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-black dark:peer-checked:bg-white"></div>
											</label>
											<span class="text-sm text-gray-700 dark:text-gray-300">
												{_user.gmail_sync_enabled === 1 ? $i18n.t('Enabled') : $i18n.t('Disabled')}
											</span>
										</div>
										<div class="text-xs text-gray-500 mt-1">
											{$i18n.t('Allow this user to sync Gmail emails for search')}
										</div>
										
										{#if _user.gmail_sync_enabled === 1}
											<div class="mt-2">
												<button
													type="button"
													class="px-3 py-1.5 text-xs font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 rounded-lg transition"
													on:click={handleForceGmailSync}
												>
													{$i18n.t('Force Full Sync')}
												</button>
												<div class="text-xs text-gray-500 mt-1">
													{$i18n.t('Trigger a complete re-sync of all Gmail emails')}
												</div>
											</div>
										{/if}
									</div>

									<!-- Spend Limits Section -->
									<div class="flex flex-col w-full pt-3 border-t border-gray-100 dark:border-gray-800 mt-3">
										<div class="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">
											{$i18n.t('Spend Limits')}
										</div>

										{#if spendLimits !== null}
											<!-- Current Usage -->
											<div class="mb-3 p-2 bg-gray-50 dark:bg-gray-800 rounded-lg text-xs">
												<div class="grid grid-cols-2 gap-2">
													<div>
														<span class="text-gray-500">{$i18n.t('Daily Spend')}:</span>
														<span class="font-medium ml-1">${spendLimits.daily_spend?.toFixed(4) ?? '0.00'}</span>
													</div>
													<div>
														<span class="text-gray-500">{$i18n.t('Monthly Spend')}:</span>
														<span class="font-medium ml-1">${spendLimits.monthly_spend?.toFixed(4) ?? '0.00'}</span>
													</div>
													<div>
														<span class="text-gray-500">{$i18n.t('Daily Requests')}:</span>
														<span class="font-medium ml-1">{spendLimits.daily_requests ?? 0}</span>
													</div>
													<div>
														<span class="text-gray-500">{$i18n.t('Monthly Requests')}:</span>
														<span class="font-medium ml-1">{spendLimits.monthly_requests ?? 0}</span>
													</div>
												</div>
											</div>

											<!-- Enable/Disable Limits -->
											<div class="flex items-center space-x-2 mb-2">
												<label class="relative inline-flex items-center cursor-pointer">
													<input
														type="checkbox"
														class="sr-only peer"
														bind:checked={spendLimitEnabled}
													/>
													<div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-gray-300 dark:peer-focus:ring-gray-600 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-black dark:peer-checked:bg-white"></div>
												</label>
												<span class="text-sm text-gray-700 dark:text-gray-300">
													{spendLimitEnabled ? $i18n.t('Limits Enabled') : $i18n.t('Limits Disabled')}
												</span>
											</div>

											{#if spendLimitEnabled}
												<!-- Limit Inputs -->
												<div class="grid grid-cols-2 gap-2 mb-2">
													<div>
														<div class="text-xs text-gray-500 mb-1">{$i18n.t('Daily Limit ($)')}</div>
														<input
															type="number"
															step="0.01"
															min="0"
															class="w-full text-sm bg-transparent border border-gray-200 dark:border-gray-700 rounded px-2 py-1 outline-none"
															placeholder="No limit"
															bind:value={spendLimitDaily}
														/>
													</div>
													<div>
														<div class="text-xs text-gray-500 mb-1">{$i18n.t('Monthly Limit ($)')}</div>
														<input
															type="number"
															step="0.01"
															min="0"
															class="w-full text-sm bg-transparent border border-gray-200 dark:border-gray-700 rounded px-2 py-1 outline-none"
															placeholder="No limit"
															bind:value={spendLimitMonthly}
														/>
													</div>
												</div>
											{/if}
										{:else}
											<div class="text-xs text-gray-500">{$i18n.t('Loading spend data...')}</div>
										{/if}
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
</style>
