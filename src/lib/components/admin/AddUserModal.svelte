<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher } from 'svelte';
	import { onMount, getContext } from 'svelte';
	import { addUser } from '$lib/apis/auths';

	import Modal from '../common/Modal.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;

	let _user = {
		name: '',
		email: '',
		password: '',
		role: 'pending'
	};

	$: if (show) {
		_user = {
			name: '',
			email: '',
			password: '',
			role: 'pending'
		};
	}

	const submitHandler = async () => {
		const res = await addUser(
			localStorage.token,
			_user.name,
			_user.email,
			_user.password,
			_user.role
		).catch((error) => {
			toast.error(error);
		});

		if (res) {
			dispatch('save');
			show = false;
		}
	};
</script>

<Modal size="sm" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-2">
			<div class=" text-lg font-medium self-center">{$i18n.t('Add User')}</div>
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

		<div class="flex flex-col md:flex-row w-full px-5 pb-4 md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div class=" ">
						<div class="flex flex-col w-full">
							<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Role')}</div>

							<div class="flex-1">
								<select
									class="w-full capitalize rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 disabled:text-gray-500 dark:disabled:text-gray-500 outline-none"
									bind:value={_user.role}
									placeholder={$i18n.t('Enter Your Role')}
									required
								>
									<option value="pending"> pending </option>
									<option value="user"> user </option>
									<option value="admin"> admin </option>
								</select>
							</div>
						</div>

						<div class="flex flex-col w-full mt-2">
							<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Name')}</div>

							<div class="flex-1">
								<input
									class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 disabled:text-gray-500 dark:disabled:text-gray-500 outline-none"
									type="text"
									bind:value={_user.name}
									placeholder={$i18n.t('Enter Your Full Name')}
									autocomplete="off"
									required
								/>
							</div>
						</div>

						<hr class=" dark:border-gray-800 my-3 w-full" />

						<div class="flex flex-col w-full">
							<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Email')}</div>

							<div class="flex-1">
								<input
									class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 disabled:text-gray-500 dark:disabled:text-gray-500 outline-none"
									type="email"
									bind:value={_user.email}
									placeholder={$i18n.t('Enter Your Email')}
									autocomplete="off"
									required
								/>
							</div>
						</div>

						<div class="flex flex-col w-full mt-2">
							<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Password')}</div>

							<div class="flex-1">
								<input
									class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 disabled:text-gray-500 dark:disabled:text-gray-500 outline-none"
									type="password"
									bind:value={_user.password}
									placeholder={$i18n.t('Enter Your Password')}
									autocomplete="off"
								/>
							</div>
						</div>
					</div>

					<div class="flex justify-end pt-3 text-sm font-medium">
						<button
							class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
							type="submit"
						>
							{$i18n.t('Submit')}
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
