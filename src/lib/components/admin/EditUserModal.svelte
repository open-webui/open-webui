<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import { createEventDispatcher } from 'svelte';
	import { onMount, getContext } from 'svelte';

	import { updateUserById } from '$lib/apis/users';
	import Modal from '../common/Modal.svelte';

	import { models } from '$lib/stores';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let selectedUser;
	export let sessionUser;

	let _user = {
		profile_image_url: '',
		name: '',
		email: '',
		password: '',
		models: '',
		whitelist_enabled: false
	};

	let whitelistEnabled = false;
	let whitelistModels = [''];

	const submitHandler = async () => {
		if (whitelistEnabled) {
			_user.models = JSON.stringify(whitelistModels);
			_user.whitelist_enabled = whitelistEnabled;
		}
		const res = await updateUserById(localStorage.token, selectedUser.id, _user).catch((error) => {
			toast.error(error);
		});

		if (res) {
			dispatch('save');
			show = false;
		}
	};

	onMount(() => {
		if (selectedUser) {
			_user = selectedUser;
			_user.password = '';
			whitelistModels = JSON.parse(selectedUser.models).length === 0 ? [''] : JSON.parse(selectedUser.models);
			whitelistEnabled = selectedUser.whitelist_enabled
		}
	});
</script>

<Modal size="sm" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 py-4">
			<div class=" text-lg font-medium self-center">{$i18n.t('Edit User')}</div>
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
		<hr class=" dark:border-gray-800" />

		<div class="flex flex-col md:flex-row w-full p-5 md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div class=" flex items-center rounded-md py-2 px-4 w-full">
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
								{dayjs(selectedUser.created_at * 1000).format($i18n.t('MMMM DD, YYYY'))}
							</div>
						</div>
					</div>

					<hr class=" dark:border-gray-800 my-3 w-full" />

					<div class=" flex flex-col space-y-1.5">
						<div class="flex flex-col w-full">
							<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Email')}</div>

							<div class="flex-1">
								<input
									class="w-full rounded py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 disabled:text-gray-500 dark:disabled:text-gray-500 outline-none"
									type="email"
									bind:value={_user.email}
									autocomplete="off"
									required
									disabled={_user.id == sessionUser.id}
								/>
							</div>
						</div>

						<div class="flex flex-col w-full">
							<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Name')}</div>

							<div class="flex-1">
								<input
									class="w-full rounded py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none"
									type="text"
									bind:value={_user.name}
									autocomplete="off"
									required
								/>
							</div>
						</div>

						<div class="flex flex-col w-full">
							<div class=" mb-1 text-xs text-gray-500">{$i18n.t('New Password')}</div>

							<div class="flex-1">
								<input
									class="w-full rounded py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none"
									type="password"
									bind:value={_user.password}
									autocomplete="new-password"
								/>
							</div>
						</div>
					</div>


					<div class="mt-2 space-y-3 pr-1.5">
						<div>
							<div class="mb-2">
								<div class="flex justify-between items-center text-xs">
									<div class=" text-sm font-medium">{$i18n.t('Manage Models')}</div>
								</div>
							</div>
			
							<div class=" space-y-3">
								<div>
									<div class="flex justify-between items-center text-xs">
										<div class=" text-xs font-medium">{$i18n.t('Model Whitelisting')}</div>
			
										<button
											class=" text-xs font-medium text-gray-500"
											type="button"
											on:click={() => {
												whitelistEnabled = !whitelistEnabled;
											}}>{whitelistEnabled ? $i18n.t('On') : $i18n.t('Off')}</button
										>
									</div>
								</div>
			
								{#if whitelistEnabled}
									<div>
										<div class=" space-y-1.5">
											{#each whitelistModels as modelId, modelIdx}
												<div class="flex w-full">
													<div class="flex-1 mr-2">
														<select
															class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
															bind:value={modelId}
															placeholder="Select a model"
														>
															<option value="" disabled selected>{$i18n.t('Select a model')}</option>
															{#each $models.filter((model) => model.id) as model}
																<option value={model.id} class="bg-gray-100 dark:bg-gray-700"
																	>{model.name}</option
																>
															{/each}
														</select>
													</div>
			
													{#if modelIdx === 0}
														<button
															class="px-2.5 bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-900 dark:text-white rounded-lg transition"
															type="button"
															on:click={() => {
																if (whitelistModels.at(-1) !== '') {
																	whitelistModels = [...whitelistModels, ''];
																}
															}}
														>
															<svg
																xmlns="http://www.w3.org/2000/svg"
																viewBox="0 0 16 16"
																fill="currentColor"
																class="w-4 h-4"
															>
																<path
																	d="M8.75 3.75a.75.75 0 0 0-1.5 0v3.5h-3.5a.75.75 0 0 0 0 1.5h3.5v3.5a.75.75 0 0 0 1.5 0v-3.5h3.5a.75.75 0 0 0 0-1.5h-3.5v-3.5Z"
																/>
															</svg>
														</button>
													{:else}
														<button
															class="px-2.5 bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-900 dark:text-white rounded-lg transition"
															type="button"
															on:click={() => {
																whitelistModels.splice(modelIdx, 1);
																whitelistModels = whitelistModels;
															}}
														>
															<svg
																xmlns="http://www.w3.org/2000/svg"
																viewBox="0 0 16 16"
																fill="currentColor"
																class="w-4 h-4"
															>
																<path d="M3.75 7.25a.75.75 0 0 0 0 1.5h8.5a.75.75 0 0 0 0-1.5h-8.5Z" />
															</svg>
														</button>
													{/if}
												</div>
											{/each}
										</div>
			
										<div class="flex justify-end items-center text-xs mt-1.5 text-right">
											<div class=" text-xs font-medium">
												{whitelistModels.length}
												{$i18n.t('Model(s) Whitelisted')}
											</div>
										</div>
									</div>
								{/if}
							</div>
						</div>
					</div>

					<div class="flex justify-end pt-3 text-sm font-medium">
						<button
							class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
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
