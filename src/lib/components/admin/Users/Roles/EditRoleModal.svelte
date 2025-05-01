<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import { createEventDispatcher } from 'svelte';
	import { onMount, getContext } from 'svelte';

	import { updateRole, getRolePermissions, linkRoleToPermissions } from '$lib/apis/roles';
    import { getUserDefaultPermissions } from '$lib/apis/users'

	import Modal from '$lib/components/common/Modal.svelte';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import Permissions from "$lib/components/common/Permissions.svelte";
	import WrenchSolid from "$lib/components/icons/WrenchSolid.svelte";
	import Plus from "$lib/components/icons/Plus.svelte";

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();
	dayjs.extend(localizedFormat);

	export let show = false;
	export let selectedRole;
	export let tabs = ['general', 'permissions'];
	export let lockedRoles = ['pending', 'user', 'admin']

	let selectedTab = 'general';
	let defaultPermissions = {};
	let permissions = {};
	let _role = {
		id: '',
		name: '',
	};

	const submitHandler = async () => {
		const res = await updateRole(localStorage.token, selectedRole.id, _role.name).catch((error) => {
			toast.error(`${error}`);
		});

		if (res) {
			// Loop through permissions and link them to the role
			for (const [categoryName, category] of Object.entries(permissions)) {
				for (const [permissionName, value] of Object.entries(category)) {
					await linkRoleToPermissions(localStorage.token, _role.name, categoryName, permissionName, value).catch((error) => {
						toast.error(`Failed to link permission ${permissionName}: ${error}`);
					});
				}
			}

			dispatch('save');
			show = false;
		}
	};


	onMount(async () => {
		if (selectedRole) {
			_role = selectedRole;

			defaultPermissions = await getUserDefaultPermissions(localStorage.token).catch((error) => {
				toast.error(`${error}`);
				return [];
			});

			permissions = await getRolePermissions(localStorage.token, _role.name).catch((error) => {
				toast.error(`${error}`);
				return [];
			});
		}
	});
</script>

<Modal size="md" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 py-4">
			<div class=" text-lg font-medium self-center">{$i18n.t('Edit Role')}</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>
		<hr class="border-gray-100 dark:border-gray-850" />

		<div class="flex flex-col md:flex-row w-full px-4 pb-4 md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full"
					on:submit={(e) => {
						e.preventDefault();
						submitHandler();
					}}
				>
					<div class="flex flex-col lg:flex-row w-full h-full pb-2 lg:space-x-4">
						<div
							id="admin-settings-tabs-container"
							class="tabs flex flex-row overflow-x-auto gap-2.5 max-w-full lg:gap-1 lg:flex-col lg:flex-none lg:w-40 dark:text-gray-200 text-sm font-medium text-left scrollbar-none"
						>
							{#if tabs.includes('general')}
								<button
									class="px-0.5 py-1 max-w-fit w-fit rounded-lg flex-1 lg:flex-none flex text-right transition {selectedTab ===
									'general'
										? ''
										: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
									on:click={() => {
										selectedTab = 'general';
									}}
									type="button"
								>
									<div class=" self-center mr-2">
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 16 16"
											fill="currentColor"
											class="w-4 h-4"
										>
											<path
												fill-rule="evenodd"
												d="M6.955 1.45A.5.5 0 0 1 7.452 1h1.096a.5.5 0 0 1 .497.45l.17 1.699c.484.12.94.312 1.356.562l1.321-1.081a.5.5 0 0 1 .67.033l.774.775a.5.5 0 0 1 .034.67l-1.08 1.32c.25.417.44.873.561 1.357l1.699.17a.5.5 0 0 1 .45.497v1.096a.5.5 0 0 1-.45.497l-1.699.17c-.12.484-.312.94-.562 1.356l1.082 1.322a.5.5 0 0 1-.034.67l-.774.774a.5.5 0 0 1-.67.033l-1.322-1.08c-.416.25-.872.44-1.356.561l-.17 1.699a.5.5 0 0 1-.497.45H7.452a.5.5 0 0 1-.497-.45l-.17-1.699a4.973 4.973 0 0 1-1.356-.562L4.108 13.37a.5.5 0 0 1-.67-.033l-.774-.775a.5.5 0 0 1-.034-.67l1.08-1.32a4.971 4.971 0 0 1-.561-1.357l-1.699-.17A.5.5 0 0 1 1 8.548V7.452a.5.5 0 0 1 .45-.497l1.699-.17c.12-.484.312-.94.562-1.356L2.629 4.107a.5.5 0 0 1 .034-.67l.774-.774a.5.5 0 0 1 .67-.033L5.43 3.71a4.97 4.97 0 0 1 1.356-.561l.17-1.699ZM6 8c0 .538.212 1.026.558 1.385l.057.057a2 2 0 0 0 2.828-2.828l-.058-.056A2 2 0 0 0 6 8Z"
												clip-rule="evenodd"
											/>
										</svg>
									</div>
									<div class=" self-center">{$i18n.t('General')}</div>
								</button>
							{/if}

							{#if tabs.includes('permissions')}
								<button
									class="px-0.5 py-1 max-w-fit w-fit rounded-lg flex-1 lg:flex-none flex text-right transition {selectedTab ===
									'permissions'
										? ''
										: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
									on:click={() => {
										selectedTab = 'permissions';
									}}
									type="button"
								>
									<div class=" self-center mr-2">
										<WrenchSolid />
									</div>
									<div class="self-center">{$i18n.t('Permissions')}</div>
								</button>
							{/if}
						</div>

						<div
							class="flex-1 mt-1 lg:mt-1 lg:h-[22rem] lg:max-h-[22rem] overflow-y-auto scrollbar-hidden"
						>
							{#if selectedTab === 'general'}
								<div class="flex flex-col w-full mt-1">
									<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Name')}</div>

									<div class="flex-1">
										<input
											class="w-full text-sm bg-transparent disabled:text-gray-500 dark:disabled:text-gray-500 outline-hidden"
											type="text"
											bind:value={_role.name}
											placeholder={$i18n.t('Role name, should be lower case and without spaces')}
											autocomplete="off"
											required
											disabled="{lockedRoles.includes(_role.name) ? 'disabled' : ''}"
										/>
									</div>
								</div>
							{:else if selectedTab === 'permissions'}
								<Permissions bind:permissions bind:defaultPermissions />
							{/if}
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
				</form>
			</div>
		</div>
	</div>
</Modal>
