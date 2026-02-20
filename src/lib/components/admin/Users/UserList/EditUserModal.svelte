<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import { createEventDispatcher } from 'svelte';
	import { onMount, getContext } from 'svelte';
	import { slide } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';

	import { goto } from '$app/navigation';

	import { updateUserById, getUserGroupsById } from '$lib/apis/users';
	import { getRoles } from '$lib/apis/roles';
	import { getSharepointTenants, getSharepointSites } from '$lib/apis/sharepoint';
	import type { TenantInfo, SiteInfo } from '$lib/apis/sharepoint';

	import Modal from '$lib/components/common/Modal.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import XMark from '$lib/components/icons/XMark.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import UserProfileImage from '$lib/components/chat/Settings/Account/UserProfileImage.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();
	dayjs.extend(localizedFormat);

	export let show = false;
	export let selectedUser;
	export let sessionUser;

	$: if (show) {
		init();
	}

	let roles: { id: string; name: string; description?: string; is_system: boolean }[] = [];

	// SharePoint state
	let sharepointSectionOpen = false;
	let sharepointTenants: TenantInfo[] = [];
	let sharepointSites: SiteInfo[] = [];
	let sharepointLoading = false;
	let sharepointConfigured = false;
	let restrictSites = false;
	let allowedSites: string[] = [];
	let siteSearchQuery = '';

	$: filteredSites = sharepointSites.filter((site) =>
		site.display_name.toLowerCase().includes(siteSearchQuery.toLowerCase())
	);

	const init = async () => {
		if (selectedUser) {
			_user = selectedUser;
			_user.password = '';
			loadUserGroups();
			loadSharepointConfig();
			await loadRoles();
		}
	};

	const loadRoles = async () => {
		try {
			const res = await getRoles(localStorage.token);
			if (res?.items) {
				roles = res.items;
			}
		} catch (err) {
			console.error('Failed to load roles:', err);
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
		// Build info payload with sharepoint config
		const sharepointInfo = sharepointConfigured
			? {
					sharepoint: {
						restrict_sites: restrictSites,
						allowed_sites: restrictSites ? allowedSites : []
					}
				}
			: undefined;

		const res = await updateUserById(localStorage.token, selectedUser.id, {
			..._user,
			info: sharepointInfo
		}).catch((error) => {
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

	const loadSharepointConfig = async () => {
		sharepointLoading = true;
		sharepointSectionOpen = false;
		siteSearchQuery = '';

		try {
			sharepointTenants = await getSharepointTenants(localStorage.token);
			sharepointConfigured = sharepointTenants.length > 0;

			if (sharepointConfigured && sharepointTenants.length > 0) {
				// Load sites from the first tenant
				sharepointSites = await getSharepointSites(localStorage.token, sharepointTenants[0].id);
			}

			// Load existing user config
			const spConfig = selectedUser?.info?.sharepoint;
			if (spConfig) {
				restrictSites = spConfig.restrict_sites ?? false;
				allowedSites = spConfig.allowed_sites ?? [];
			} else {
				restrictSites = false;
				allowedSites = [];
			}
		} catch (err) {
			console.error('Failed to load SharePoint config:', err);
			sharepointConfigured = false;
		} finally {
			sharepointLoading = false;
		}
	};

	const toggleSiteAccess = (siteName: string) => {
		if (allowedSites.includes(siteName)) {
			allowedSites = allowedSites.filter((s) => s !== siteName);
		} else {
			allowedSites = [...allowedSites, siteName];
		}
	};
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
												class="w-full dark:bg-gray-900 text-sm bg-transparent disabled:text-gray-500 dark:disabled:text-gray-500 outline-hidden capitalize"
												bind:value={_user.role}
												disabled={_user.id == sessionUser.id}
												required
											>
												{#if roles.length > 0}
													{#each roles as role}
														<option value={role.name}>{role.name}</option>
													{/each}
												{:else}
													<option value="admin">{$i18n.t('Admin')}</option>
													<option value="user">{$i18n.t('User')}</option>
													<option value="pending">{$i18n.t('Pending')}</option>
												{/if}
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

						<!-- SharePoint Access Section -->
						{#if sharepointConfigured}
							<div class="mt-4 border-t border-gray-100 dark:border-gray-800 pt-3">
								<!-- svelte-ignore a11y-no-static-element-interactions -->
								<!-- svelte-ignore a11y-click-events-have-key-events -->
								<div
									class="flex items-center justify-between cursor-pointer select-none group"
									on:click={() => {
										sharepointSectionOpen = !sharepointSectionOpen;
									}}
								>
									<div class="flex items-center gap-2">
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 24 24"
											fill="none"
											stroke="currentColor"
											stroke-width="1.5"
											stroke-linecap="round"
											stroke-linejoin="round"
											class="size-4 text-accent-500 dark:text-accent-400"
										>
											<path d="M4 22h14a2 2 0 0 0 2-2V7l-5-5H6a2 2 0 0 0-2 2v4" />
											<path d="M14 2v5h5" />
											<path d="m3 15 2 2 4-4" />
										</svg>
										<span class="text-sm font-medium text-gray-700 dark:text-gray-300">
											{$i18n.t('SharePoint Access')}
										</span>
										{#if restrictSites}
											<span
												class="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-accent-500/10 text-accent-600 dark:text-accent-400"
											>
												{allowedSites.length}
												{allowedSites.length === 1 ? $i18n.t('site') : $i18n.t('sites')}
											</span>
										{/if}
									</div>
									<div
										class="text-gray-400 dark:text-gray-500 group-hover:text-gray-600 dark:group-hover:text-gray-300 transition-transform duration-200"
										class:rotate-180={sharepointSectionOpen}
									>
										<ChevronDown className="size-4" strokeWidth="2" />
									</div>
								</div>

								{#if sharepointSectionOpen}
									<div
										class="mt-3 space-y-3"
										transition:slide={{ duration: 200, easing: quintOut }}
									>
										<!-- Restrict toggle -->
										<div
											class="flex items-center justify-between rounded-lg bg-gray-50 dark:bg-gray-900/50 px-3 py-2.5"
										>
											<div class="flex flex-col">
												<span class="text-sm text-gray-700 dark:text-gray-300">
													{$i18n.t('Restrict SharePoint Access')}
												</span>
												<span class="text-xs text-gray-400 dark:text-gray-500">
													{$i18n.t('Limit which sites this user can browse')}
												</span>
											</div>
											<Switch bind:state={restrictSites} tooltip />
										</div>

										<!-- Site selection -->
										{#if restrictSites}
											<div
												class="rounded-lg border border-gray-150 dark:border-gray-800 overflow-hidden"
												transition:slide={{ duration: 200, easing: quintOut }}
											>
												<!-- Search -->
												{#if sharepointSites.length > 5}
													<div class="px-3 py-2 border-b border-gray-100 dark:border-gray-800">
														<input
															type="text"
															class="w-full text-sm bg-transparent outline-hidden placeholder-gray-400 dark:placeholder-gray-500"
															placeholder={$i18n.t('Search sites...')}
															bind:value={siteSearchQuery}
														/>
													</div>
												{/if}

												<!-- Site list -->
												<div class="max-h-48 overflow-y-auto">
													{#if sharepointLoading}
														<div
															class="flex items-center justify-center py-6 text-sm text-gray-400"
														>
															<svg
																class="animate-spin size-4 mr-2"
																xmlns="http://www.w3.org/2000/svg"
																fill="none"
																viewBox="0 0 24 24"
															>
																<circle
																	class="opacity-25"
																	cx="12"
																	cy="12"
																	r="10"
																	stroke="currentColor"
																	stroke-width="4"
																/>
																<path
																	class="opacity-75"
																	fill="currentColor"
																	d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
																/>
															</svg>
															{$i18n.t('Loading sites...')}
														</div>
													{:else if filteredSites.length === 0}
														<div class="py-6 text-center text-sm text-gray-400 dark:text-gray-500">
															{siteSearchQuery
																? $i18n.t('No sites match your search')
																: $i18n.t('No sites available')}
														</div>
													{:else}
														{#each filteredSites as site (site.id)}
															{@const isSelected = allowedSites.includes(site.display_name)}
															<!-- svelte-ignore a11y-no-static-element-interactions -->
															<!-- svelte-ignore a11y-click-events-have-key-events -->
															<div
																class="flex items-center gap-3 px-3 py-2 cursor-pointer transition-colors
																	{isSelected
																	? 'bg-accent-500/5 dark:bg-accent-400/5'
																	: 'hover:bg-gray-50 dark:hover:bg-gray-900/30'}"
																on:click={() => toggleSiteAccess(site.display_name)}
															>
																<div
																	class="flex items-center justify-center size-4 rounded border transition-colors flex-shrink-0
																		{isSelected
																		? 'bg-accent-500 dark:bg-accent-400 border-accent-500 dark:border-accent-400'
																		: 'border-gray-300 dark:border-gray-600'}"
																>
																	{#if isSelected}
																		<svg
																			xmlns="http://www.w3.org/2000/svg"
																			viewBox="0 0 24 24"
																			fill="none"
																			stroke="white"
																			stroke-width="3"
																			stroke-linecap="round"
																			stroke-linejoin="round"
																			class="size-3"
																		>
																			<polyline points="20 6 9 17 4 12" />
																		</svg>
																	{/if}
																</div>
																<div class="flex flex-col min-w-0">
																	<span
																		class="text-sm truncate {isSelected
																			? 'text-gray-800 dark:text-gray-200 font-medium'
																			: 'text-gray-600 dark:text-gray-400'}"
																	>
																		{site.display_name}
																	</span>
																</div>
															</div>
														{/each}
													{/if}
												</div>

												<!-- Footer summary -->
												{#if allowedSites.length > 0}
													<div
														class="px-3 py-2 border-t border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/30"
													>
														<div class="flex items-center justify-between">
															<span class="text-xs text-gray-500 dark:text-gray-400">
																{allowedSites.length}
																{allowedSites.length === 1
																	? $i18n.t('site selected')
																	: $i18n.t('sites selected')}
															</span>
															<!-- svelte-ignore a11y-no-static-element-interactions -->
															<!-- svelte-ignore a11y-click-events-have-key-events -->
															<span
																class="text-xs text-accent-500 dark:text-accent-400 cursor-pointer hover:underline"
																on:click|stopPropagation={() => {
																	allowedSites = [];
																}}
															>
																{$i18n.t('Clear all')}
															</span>
														</div>
													</div>
												{/if}
											</div>
										{/if}
									</div>
								{/if}
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
