<script lang="ts">
	import { getContext, onMount } from 'svelte';

	const i18n = getContext('i18n');

	import { getGroups } from '$lib/apis/groups';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import UserCircleSolid from '$lib/components/icons/UserCircleSolid.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Badge from '$lib/components/common/Badge.svelte';

	export let onChange: Function = () => {};

	export let accessRoles = ['read'];
	export let accessControl = {};

	export let allowPublic = true;

	// Local state for UI changes - only committed to parent when explicitly requested
	let localAccessControl = {};
	let selectedGroupId = '';
	let groups = [];

	// Function to get the current local access control for the parent to read
	export function getLocalAccessControl() {
		return localAccessControl;
	}

	// Track if we're in the middle of committing to avoid sync loops
	let isCommitting = false;
	let lastAccessControlString = '';

	// Sync external changes to local state (e.g., when parent resets)
	// Only sync when we're not in the middle of committing our own changes
	// and when accessControl actually changed externally
	$: {
		if (accessControl && !isCommitting) {
			const currentAccessControlString = JSON.stringify(accessControl);
			if (currentAccessControlString !== lastAccessControlString) {
				console.log('SYNC: External accessControl changed, syncing to local state');
				console.log('SYNC: Previous:', lastAccessControlString);
				console.log('SYNC: Current:', currentAccessControlString);
				localAccessControl = JSON.parse(JSON.stringify(accessControl));
				lastAccessControlString = currentAccessControlString;
				console.log('SYNC: New localAccessControl after sync:', localAccessControl);
			} else {
				console.log('SYNC: accessControl unchanged, skipping sync');
			}
		}
	}

	// Function to commit local changes to parent
	export function commitChanges() {
		isCommitting = true;
		accessControl = JSON.parse(JSON.stringify(localAccessControl));
		lastAccessControlString = JSON.stringify(accessControl);
		onChange(accessControl);
		// Reset the flag after a tick to allow future syncs
		setTimeout(() => { isCommitting = false; }, 0);
	}

	$: if (!allowPublic && accessControl === null) {
		accessControl = {
			read: {
				group_ids: [],
				user_ids: []
			},
			write: {
				group_ids: [],
				user_ids: []
			},
			inspect: {
				group_ids: [],
				user_ids: []
			}
		};
		localAccessControl = JSON.parse(JSON.stringify(accessControl));
		lastAccessControlString = JSON.stringify(accessControl);
		onChange(accessControl);
	}

	onMount(async () => {
		groups = await getGroups(localStorage.token);

		if (accessControl === null) {
			if (allowPublic) {
				localAccessControl = null;
			} else {
				// This will be handled by the reactive statement above
			}
		} else {
			// Ensure accessControl has all required properties
			accessControl = {
				read: {
					group_ids: accessControl?.read?.group_ids ?? [],
					user_ids: accessControl?.read?.user_ids ?? []
				},
				write: {
					group_ids: accessControl?.write?.group_ids ?? [],
					user_ids: accessControl?.write?.user_ids ?? []
				},
				inspect: {
					group_ids: accessControl?.inspect?.group_ids ?? [],
					user_ids: accessControl?.inspect?.user_ids ?? []
				}
			};
			// Initialize local state with current access control
			localAccessControl = JSON.parse(JSON.stringify(accessControl));
			lastAccessControlString = JSON.stringify(accessControl);
		}
	});

	$: if (selectedGroupId) {
		console.log('Reactive statement triggered with selectedGroupId:', selectedGroupId);
		onSelectGroup();
	}

	const onSelectGroup = () => {
		console.log('onSelectGroup called with:', selectedGroupId);
		console.log('localAccessControl before:', localAccessControl);
		if (selectedGroupId !== '') {
			// Ensure localAccessControl is properly initialized  
			if (!localAccessControl || !localAccessControl.read) {
				console.log('Initializing localAccessControl');
				localAccessControl = {
					read: { group_ids: [], user_ids: [] },
					write: { group_ids: [], user_ids: [] },
					inspect: { group_ids: [], user_ids: [] }
				};
			}
			
			localAccessControl.read.group_ids = [...localAccessControl.read.group_ids, selectedGroupId];
			console.log('Updated localAccessControl after adding group:', localAccessControl);
			
			// Trigger Svelte reactivity by reassigning the object
			localAccessControl = { ...localAccessControl };
			console.log('Final localAccessControl after reactivity trigger:', localAccessControl);
			
			selectedGroupId = '';
		}
	};
</script>

<div class=" rounded-lg flex flex-col gap-2">
	<div class="">
		<div class=" text-sm font-semibold mb-1">{$i18n.t('Visibility')}</div>

		<div class="flex gap-2.5 items-center mb-1">
			<div>
				<div class=" p-2 bg-black/5 dark:bg-white/5 rounded-full">
					{#if localAccessControl !== null}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="w-5 h-5"
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
							class="w-5 h-5"
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

			<div>
				<select
					id="models"
					class="outline-hidden bg-transparent text-sm font-medium rounded-lg block w-fit pr-10 max-w-full placeholder-gray-400"
					value={localAccessControl !== null ? 'private' : 'public'}
					on:change={(e) => {
						if (e.target.value === 'public') {
							localAccessControl = null;
						} else {
							localAccessControl = {
								read: {
									group_ids: [],
									user_ids: []
								},
								write: {
									group_ids: [],
									user_ids: []
								},
								inspect: {
									group_ids: [],
									user_ids: []
								}
							};
						}
					}}
				>
					<option class=" text-gray-700" value="private" selected>{$i18n.t('Private')}</option>
					{#if allowPublic}
						<option class=" text-gray-700" value="public" selected>{$i18n.t('Public')}</option>
					{/if}
				</select>

				<div class=" text-xs text-gray-400 font-medium">
					{#if localAccessControl !== null}
						{$i18n.t('Only select users and groups with permission can access')}
					{:else}
						{$i18n.t('Accessible to all users')}
					{/if}
				</div>
			</div>
		</div>
	</div>
	{#if localAccessControl !== null}
		{@const accessGroups = groups.filter((group) =>
			localAccessControl?.read?.group_ids?.includes(group.id)
		)}
		{@const availableGroups = groups.filter((group) => !localAccessControl?.read?.group_ids?.includes(group.id))}
		{(() => {
			console.log('Template rendering with:');
			console.log('- localAccessControl:', localAccessControl);
			console.log('- groups:', groups);
			console.log('- accessGroups (should show in UI):', accessGroups);
			console.log('- availableGroups (in dropdown):', availableGroups);
			return '';
		})()}
		<div>
			<div class="">
				<div class="flex justify-between mb-1.5">
					<div class="text-sm font-semibold">
						{$i18n.t('Groups')}
					</div>
				</div>

				<div class="mb-1">
					<div class="flex w-full">
						<div class="flex flex-1 items-center">
							<div class="w-full px-0.5">
								<select
									class="outline-hidden bg-transparent text-sm rounded-lg block w-full pr-10 max-w-full
									{selectedGroupId ? '' : 'text-gray-500'}
									dark:placeholder-gray-500"
									bind:value={selectedGroupId}
								>
									<option class=" text-gray-700" value="" disabled selected
										>{$i18n.t('Select a group')}</option
									>
									{#each groups.filter((group) => !localAccessControl?.read?.group_ids?.includes(group.id)) as group}
										<option class=" text-gray-700" value={group.id}>{group.name}</option>
									{/each}
								</select>
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

				<hr class=" border-gray-100 dark:border-gray-700/10 mt-1.5 mb-2.5 w-full" />

				<div class="flex flex-col gap-2 mb-1 px-0.5">
					{#if accessGroups.length > 0}
						{#each accessGroups as group}
							<div class="flex items-center gap-3 justify-between text-xs w-full transition">
								<div class="flex items-center gap-1.5 w-full font-medium">
									<div>
										<UserCircleSolid className="size-4" />
									</div>

									<div>
										{group.name}
									</div>
								</div>

								<div class="w-full flex justify-end items-center gap-0.5">
									<button
										class=""
										type="button"
										on:click={() => {
											// Cycle through permissions: read → write → inspect → read
											// NOTE: Groups always remain in read.group_ids for UI display
											if (localAccessControl.inspect.group_ids.includes(group.id)) {
												// Currently inspect, remove from inspect and write, back to read-only
												localAccessControl.inspect.group_ids = localAccessControl.inspect.group_ids.filter(
													(group_id) => group_id !== group.id
												);
												localAccessControl.write.group_ids = localAccessControl.write.group_ids.filter(
													(group_id) => group_id !== group.id
												);
												// Group remains in read.group_ids for UI display
											} else if (localAccessControl.write.group_ids.includes(group.id)) {
												// Currently write, move to inspect if available
												if (accessRoles.includes('inspect')) {
													// Remove from write and add to inspect
													localAccessControl.write.group_ids = localAccessControl.write.group_ids.filter(
														(group_id) => group_id !== group.id
													);
													localAccessControl.inspect.group_ids = [
														...localAccessControl.inspect.group_ids,
														group.id
													];
													// Group remains in read.group_ids for UI display
												} else {
													// No inspect role, just toggle back to read
													localAccessControl.write.group_ids = localAccessControl.write.group_ids.filter(
														(group_id) => group_id !== group.id
													);
													// Group remains in read.group_ids for UI display
												}
											} else {
												// Currently read, move to write if available
												if (accessRoles.includes('write')) {
													localAccessControl.write.group_ids = [
														...localAccessControl.write.group_ids,
														group.id
													];
													// Group remains in read.group_ids for UI display
												}
											}
											// Trigger Svelte reactivity
											localAccessControl = { ...localAccessControl };
										}}
									>
										{#if localAccessControl.inspect.group_ids.includes(group.id)}
											<Badge type={'warning'} content={$i18n.t('Inspect')} />
										{:else if localAccessControl.write.group_ids.includes(group.id)}
											<Badge type={'success'} content={$i18n.t('Write')} />
										{:else}
											<Badge type={'info'} content={$i18n.t('Read')} />
										{/if}
									</button>

									<button
										class=" rounded-full p-1 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
										type="button"
										on:click={() => {
											// Remove group from all permission arrays
											localAccessControl.read.group_ids = localAccessControl.read.group_ids.filter(
												(id) => id !== group.id
											);
											localAccessControl.write.group_ids = localAccessControl.write.group_ids.filter(
												(id) => id !== group.id
											);
											localAccessControl.inspect.group_ids = localAccessControl.inspect.group_ids.filter(
												(id) => id !== group.id
											);
											// Trigger Svelte reactivity
											localAccessControl = { ...localAccessControl };
										}}
									>
										<XMark />
									</button>
								</div>
							</div>
						{/each}
					{:else}
						<div class="flex items-center justify-center">
							<div class="text-gray-500 text-xs text-center py-2 px-10">
								{$i18n.t('No groups with access, add a group to grant access')}
							</div>
						</div>
					{/if}
				</div>
			</div>
		</div>
	{/if}
</div>
