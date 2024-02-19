<script>
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { config, user } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	import toast from 'svelte-french-toast';

	import { updateUserRole, getUsers, deleteUserById } from '$lib/apis/users';
	import { getSignUpEnabledStatus, toggleSignUpEnabledStatus } from '$lib/apis/auths';
	import EditUserModal from '$lib/components/admin/EditUserModal.svelte';
	import SettingsModal from '$lib/components/admin/SettingsModal.svelte';

	let loaded = false;
	let users = [];

	let selectedUser = null;

	let showSettingsModal = false;
	let showEditUserModal = false;

	const updateRoleHandler = async (id, role) => {
		const res = await updateUserRole(localStorage.token, id, role).catch((error) => {
			toast.error(error);
			return null;
		});

		if (res) {
			users = await getUsers(localStorage.token);
		}
	};

	const editUserPasswordHandler = async (id, password) => {
		const res = await deleteUserById(localStorage.token, id).catch((error) => {
			toast.error(error);
			return null;
		});
		if (res) {
			users = await getUsers(localStorage.token);
			toast.success('Successfully updated');
		}
	};

	const deleteUserHandler = async (id) => {
		const res = await deleteUserById(localStorage.token, id).catch((error) => {
			toast.error(error);
			return null;
		});
		if (res) {
			users = await getUsers(localStorage.token);
		}
	};

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
		} else {
			users = await getUsers(localStorage.token);
		}
		loaded = true;
	});
</script>

{#key selectedUser}
	<EditUserModal
		bind:show={showEditUserModal}
		{selectedUser}
		sessionUser={$user}
		on:save={async () => {
			users = await getUsers(localStorage.token);
		}}
	/>
{/key}

<SettingsModal bind:show={showSettingsModal} />

<div
	class="min-h-screen max-h-[100dvh] w-full flex justify-center dark:text-white bg-white dark:bg-gray-900 font-mona"
>
	{#if loaded}
		<div class="overflow-y-auto w-full flex justify-center">
			<div class="w-full max-w-3xl px-6 md:px-16 flex flex-col">
				<div class="py-10 w-full">
					<div class=" flex flex-col justify-center">
						<div class=" flex justify-between items-center">
							<div class=" text-2xl font-semibold">Users ({users.length})</div>
							<div>
								<button
									class="flex items-center space-x-1 border border-gray-200 dark:border-gray-600 px-3 py-1 rounded-lg"
									type="button"
									on:click={() => {
										showSettingsModal = !showSettingsModal;
									}}
								>
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

									<div class=" text-xs">Admin Settings</div>
								</button>
							</div>
						</div>
						<div class=" text-gray-500 text-xs mt-1">
							Click on the user role cell in the table to change a user's role.
						</div>

						<hr class=" my-3 dark:border-gray-600" />

						<div class="scrollbar-hidden relative overflow-x-auto whitespace-nowrap">
							<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto">
								<thead
									class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-700 dark:text-gray-400"
								>
									<tr>
										<th scope="col" class="px-3 py-2"> Role </th>
										<th scope="col" class="px-3 py-2"> Name </th>
										<th scope="col" class="px-3 py-2"> Email </th>
										<th scope="col" class="px-3 py-2"> Action </th>
									</tr>
								</thead>
								<tbody>
									{#each users as user}
										<tr class="bg-white border-b dark:bg-gray-900 dark:border-gray-700 text-xs">
											<td class="px-3 py-2 min-w-[7rem] w-28">
												<button
													class=" flex items-center gap-2 text-xs px-3 py-0.5 rounded-lg {user.role ===
														'admin' &&
														'text-sky-600 dark:text-sky-300 bg-sky-200/30'} {user.role === 'user' &&
														'text-green-600 dark:text-green-300 bg-green-200/30'} {user.role ===
														'pending' && 'text-gray-600 dark:text-gray-300 bg-gray-200/30'}"
													on:click={() => {
														if (user.role === 'user') {
															updateRoleHandler(user.id, 'admin');
														} else if (user.role === 'pending') {
															updateRoleHandler(user.id, 'user');
														} else {
															updateRoleHandler(user.id, 'pending');
														}
													}}
												>
													<div
														class="w-1 h-1 rounded-full {user.role === 'admin' &&
															'bg-sky-600 dark:bg-sky-300'} {user.role === 'user' &&
															'bg-green-600 dark:bg-green-300'} {user.role === 'pending' &&
															'bg-gray-600 dark:bg-gray-300'}"
													/>
													{user.role}</button
												>
											</td>
											<td class="px-3 py-2 font-medium text-gray-900 dark:text-white w-max">
												<div class="flex flex-row w-max">
													<img
														class=" rounded-full w-6 h-6 object-cover mr-2.5"
														src={user.profile_image_url}
														alt="user"
													/>

													<div class=" font-medium self-center">{user.name}</div>
												</div>
											</td>
											<td class=" px-3 py-2"> {user.email} </td>

											<td class="px-3 py-2">
												<div class="flex justify-start w-full space-x-1">
													<button
														class="self-center w-fit text-sm p-1.5 border dark:border-gray-600 rounded-xl flex"
														on:click={async () => {
															showEditUserModal = !showEditUserModal;
															selectedUser = user;
														}}
													>
														<svg
															xmlns="http://www.w3.org/2000/svg"
															viewBox="0 0 16 16"
															fill="currentColor"
															class="w-3.5 h-3.5"
														>
															<path
																fill-rule="evenodd"
																d="M11.013 2.513a1.75 1.75 0 0 1 2.475 2.474L6.226 12.25a2.751 2.751 0 0 1-.892.596l-2.047.848a.75.75 0 0 1-.98-.98l.848-2.047a2.75 2.75 0 0 1 .596-.892l7.262-7.261Z"
																clip-rule="evenodd"
															/>
														</svg>
													</button>

													<button
														class="self-center w-fit text-sm p-1.5 border dark:border-gray-600 rounded-xl flex"
														on:click={async () => {
															deleteUserHandler(user.id);
														}}
													>
														<svg
															xmlns="http://www.w3.org/2000/svg"
															viewBox="0 0 16 16"
															fill="currentColor"
															class="w-3.5 h-3.5"
														>
															<path
																fill-rule="evenodd"
																d="M5 3.25V4H2.75a.75.75 0 0 0 0 1.5h.3l.815 8.15A1.5 1.5 0 0 0 5.357 15h5.285a1.5 1.5 0 0 0 1.493-1.35l.815-8.15h.3a.75.75 0 0 0 0-1.5H11v-.75A2.25 2.25 0 0 0 8.75 1h-1.5A2.25 2.25 0 0 0 5 3.25Zm2.25-.75a.75.75 0 0 0-.75.75V4h3v-.75a.75.75 0 0 0-.75-.75h-1.5ZM6.05 6a.75.75 0 0 1 .787.713l.275 5.5a.75.75 0 0 1-1.498.075l-.275-5.5A.75.75 0 0 1 6.05 6Zm3.9 0a.75.75 0 0 1 .712.787l-.275 5.5a.75.75 0 0 1-1.498-.075l.275-5.5a.75.75 0 0 1 .786-.711Z"
																clip-rule="evenodd"
															/>
														</svg>
													</button>
												</div>
											</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					</div>
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
	.font-mona {
		font-family: 'Mona Sans';
	}

	.scrollbar-hidden::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.scrollbar-hidden {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
	}
</style>
