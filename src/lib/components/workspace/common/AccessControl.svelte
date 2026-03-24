<script lang="ts">
	import { getContext, onMount } from 'svelte';

	const i18n = getContext('i18n');

	import { getGroups } from '$lib/apis/groups';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SelectDropdown from '$lib/components/common/SelectDropdown.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import UserCircleSolid from '$lib/components/icons/UserCircleSolid.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Badge from '$lib/components/common/Badge.svelte';

	export let onChange: Function = () => {};

	export let accessRoles = ['read'];
	export let accessControl = {};

	export let allowPublic = true;

	let selectedGroupId = '';
	let groups = [];

	$: if (!allowPublic && accessControl === null) {
		accessControl = {
			read: {
				group_ids: [],
				user_ids: []
			},
			write: {
				group_ids: [],
				user_ids: []
			}
		};
		onChange(accessControl);
	}

	onMount(async () => {
		groups = await getGroups(localStorage.token);

		if (accessControl === null) {
			if (allowPublic) {
				accessControl = null;
			} else {
				accessControl = {
					read: {
						group_ids: [],
						user_ids: []
					},
					write: {
						group_ids: [],
						user_ids: []
					}
				};
				onChange(accessControl);
			}
		} else {
			accessControl = {
				read: {
					group_ids: accessControl?.read?.group_ids ?? [],
					user_ids: accessControl?.read?.user_ids ?? []
				},
				write: {
					group_ids: accessControl?.write?.group_ids ?? [],
					user_ids: accessControl?.write?.user_ids ?? []
				}
			};
		}
	});

	$: onChange(accessControl);

	$: if (selectedGroupId) {
		onSelectGroup();
	}

	const onSelectGroup = () => {
		if (selectedGroupId !== '') {
			accessControl.read.group_ids = [...accessControl.read.group_ids, selectedGroupId];

			selectedGroupId = '';
		}
	};
</script>

<div class="rounded-lg flex flex-col gap-3 sm:gap-4">
	<div>
		<div class="text-xs sm:text-sm font-semibold mb-2 sm:mb-3 text-gray-700 dark:text-gray-300">{$i18n.t('Visibility')}</div>

		<div class="flex gap-2.5 sm:gap-3 items-center mb-2 sm:mb-3">
			<div>
				<div class="p-2 sm:p-2.5 bg-blue-500/10 dark:bg-blue-500/20 rounded-lg">
					{#if accessControl !== null}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="w-4 h-4 sm:w-5 sm:h-5 text-blue-600 dark:text-blue-400"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"
							/>
						</svg>
					{:else}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="w-4 h-4 sm:w-5 sm:h-5 text-green-600 dark:text-green-400"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M6.115 5.19l.319 1.913A6 6 0 008.11 10.36L9.75 12l-.387.775c-.217.433-.132.956.21 1.298l1.348 1.348c.21.21.329.497.329.795v1.089c0 .426.24.815.622 1.006l.153.076c.433.217.956.132 1.298-.21l.723-.723a8.7 8.7 0 002.288-4.042 1.087 1.087 0 00-.358-1.099l-1.33-1.108c-.251-.21-.582-.299-.905-.245l-1.17.195a1.125 1.125 0 01-.98-.314l-.295-.295a1.125 1.125 0 010-1.591l.13-.132a1.125 1.125 0 011.3-.21l.603.302a.809.809 0 001.086-1.086L14.25 7.5l1.256-.837a4.5 4.5 0 001.528-1.732l.146-.292M6.115 5.19A9 9 0 1017.18 4.64M6.115 5.19A8.965 8.965 0 0112 3c1.929 0 3.716.607 5.18 1.64"
							/>
						</svg>
					{/if}
				</div>
			</div>

			<div class="flex-1">
			<SelectDropdown
				value={accessControl !== null ? 'private' : 'public'}
				options={[
					{ value: 'private', label: $i18n.t('Private') },
					...(allowPublic ? [{ value: 'public', label: $i18n.t('Public') }] : [])
				]}
				on:change={(e) => {
					if (e.detail.value === 'public') {
						accessControl = null;
					} else {
						accessControl = {
							read: {
								group_ids: [],
								user_ids: []
							},
							write: {
								group_ids: [],
								user_ids: []
							}
						};
					}
				}}
			/>
				<div class="text-xs sm:text-xs text-gray-500 dark:text-gray-400 font-medium mt-1 sm:mt-1.5">
					{#if accessControl !== null}
						{$i18n.t('Only select users and groups with permission can access')}
					{:else}
						{$i18n.t('Accessible to all users')}
					{/if}
				</div>
			</div>
		</div>
	</div>
	{#if accessControl !== null}
		{@const accessGroups = groups.filter((group) =>
			accessControl.read.group_ids.includes(group.id)
		)}
		<div>
			<div class="">
<div class="flex justify-between mb-2 sm:mb-3">
				<div class="text-xs sm:text-sm font-semibold text-gray-700 dark:text-gray-300">
					{$i18n.t('Groups')}
				</div>
			</div>

			<div class="mb-3 sm:mb-4">
				<div class="flex w-full">
					<div class="flex flex-1 items-center">
						<div class="w-full relative">
						<SelectDropdown
							value={selectedGroupId}
							options={[
								{ value: '', label: $i18n.t('Select a group') },
								...groups
									.filter((group) => !accessControl.read.group_ids.includes(group.id))
									.map((group) => ({ value: group.id, label: group.name }))
							]}
							on:change={(e) => {
								if (e.detail.value !== '') {
									accessControl.read.group_ids = [...accessControl.read.group_ids, e.detail.value];
									selectedGroupId = '';
								}
							}}
						/>
					</div>
							<!-- <div>
								<Tooltip content={$i18n.t('Add Group')}>
									<button
										class=" p-1 rounded-xl bg-transparent dark:hover:bg-white/5 hover:bg-black/5 transition font-medium text-sm flex items-center space-x-1"
										type="button"
										on:click={() => {}}
									>
										<Plus className="size-3.5" />
									</button>
								</Tooltip>
							</div> -->
						</div>
					</div>
				</div>

				<hr class="border-gray-200 dark:border-gray-700 mt-2 sm:mt-3 mb-2.5 sm:mb-3 w-full" />

				<div class="flex flex-col gap-2 sm:gap-2.5 mb-2 sm:mb-3 px-0">
					{#if accessGroups.length > 0}
						{#each accessGroups as group}
							<div class="flex items-center gap-2 sm:gap-3 justify-between text-xs w-full transition hover:bg-gray-50 dark:hover:bg-gray-750/50 p-2 sm:p-3 rounded-lg -mx-2 sm:-mx-3">
								<div class="flex items-center gap-1.5 sm:gap-2 w-full font-medium text-gray-700 dark:text-gray-300">
									<div>
										<UserCircleSolid className="size-3.5 sm:size-4 text-blue-600 dark:text-blue-400" />
									</div>

									<div class="text-xs sm:text-sm truncate">
										{group.name}
									</div>
								</div>

								<div class="w-full flex justify-end items-center gap-1 sm:gap-1.5 flex-shrink-0">
									<button
										class="transition-all duration-200"
										type="button"
										on:click={() => {
											if (accessRoles.includes('write')) {
												if (accessControl.write.group_ids.includes(group.id)) {
													accessControl.write.group_ids = accessControl.write.group_ids.filter(
														(group_id) => group_id !== group.id
													);
												} else {
													accessControl.write.group_ids = [
														...accessControl.write.group_ids,
														group.id
													];
												}
											}
										}}
									>
										{#if accessControl.write.group_ids.includes(group.id)}
											<Badge type={'success'} content={$i18n.t('Write')} />
										{:else}
											<Badge type={'info'} content={$i18n.t('Read')} />
										{/if}
									</button>

									<button
										class="rounded-full p-1.5 sm:p-2 hover:bg-red-50 dark:hover:bg-red-950/30 text-gray-500 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-all duration-200"
										type="button"
										on:click={() => {
											accessControl.read.group_ids = accessControl.read.group_ids.filter(
												(id) => id !== group.id
											);
										}}
									>
										<XMark />
									</button>
								</div>
							</div>
						{/each}
					{:else}
						<div class="flex items-center justify-center">
							<div class="text-gray-500 dark:text-gray-400 text-xs text-center py-3 sm:py-4 px-4">
								{$i18n.t('No groups with access, add a group to grant access')}
							</div>
						</div>
					{/if}
				</div>
			</div>
		</div>
	{/if}
</div>

