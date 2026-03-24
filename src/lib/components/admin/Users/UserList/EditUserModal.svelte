<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import { createEventDispatcher } from 'svelte';
	import { onMount, getContext } from 'svelte';

	import { updateUserById } from '$lib/apis/users';

	import Modal from '$lib/components/common/Modal.svelte';
	import localizedFormat from 'dayjs/plugin/localizedFormat';

	const i18n: any = getContext('i18n');
	const dispatch = createEventDispatcher();
	dayjs.extend(localizedFormat);

	export let show = false;
	export let selectedUser;
	export let sessionUser;

	let _user = {
		profile_image_url: '',
		name: '',
		email: '',
		password: ''
	};

	const submitHandler = async () => {
		const res = await updateUserById(localStorage.token, selectedUser.id, _user).catch((error) => {
			toast.error(`${error}`);
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
		}
	});
</script>

<Modal size="sm" bind:show>
	<div class="dark:text-gray-200">
		<div class="flex items-start justify-between gap-3 px-4 py-3.5 sm:px-5 sm:py-4 border-b border-gray-100 dark:border-gray-800">
			<div class="min-w-0">
				<div class="text-base sm:text-lg font-semibold text-gray-900 dark:text-gray-100">{$i18n.t('Edit User')}</div>
				<div class="mt-0.5 text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Update account details')}</div>
			</div>
			<button
				class="shrink-0 rounded-lg p-1.5 text-gray-500 hover:text-gray-900 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-gray-800 transition-colors"
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

		{#if selectedUser}
			<form
				class="p-4 sm:p-5"
				on:submit|preventDefault={() => {
					submitHandler();
				}}
			>
				<div class="flex items-center gap-3 rounded-xl border border-gray-200 dark:border-gray-800 bg-gray-50/70 dark:bg-gray-900 px-3 py-2.5">
					<img
						src={selectedUser.profile_image_url || '/user.png'}
						class="w-11 h-11 rounded-full object-cover ring-2 ring-white dark:ring-gray-800"
						alt="User profile"
					/>
					<div class="min-w-0">
						<div class="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">{selectedUser.name}</div>
						<div class="text-xs text-gray-500 dark:text-gray-400">
							{$i18n.t('Created at')} {dayjs(selectedUser.created_at * 1000).format('LL')}
						</div>
					</div>
				</div>

				<div class="mt-4 space-y-3.5">
					<div>
						<div class="mb-1.5 text-xs font-medium text-gray-600 dark:text-gray-400">{$i18n.t('Email')}</div>
						<input
							class="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2.5 text-sm text-gray-900 dark:text-gray-100 disabled:text-gray-500 dark:disabled:text-gray-500 disabled:bg-gray-50 dark:disabled:bg-gray-900 outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
							type="email"
							bind:value={_user.email}
							autocomplete="off"
							required
							disabled={selectedUser.id == sessionUser.id}
						/>
						{#if selectedUser.id == sessionUser.id}
							<div class="mt-1 text-[11px] text-gray-500 dark:text-gray-400">
								{$i18n.t('You cannot change your own account email here.')}
							</div>
						{/if}
					</div>

					<div>
						<div class="mb-1.5 text-xs font-medium text-gray-600 dark:text-gray-400">{$i18n.t('Name')}</div>
						<input
							class="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2.5 text-sm text-gray-900 dark:text-gray-100 outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
							type="text"
							bind:value={_user.name}
							autocomplete="off"
							required
						/>
					</div>

					<div>
						<div class="mb-1.5 text-xs font-medium text-gray-600 dark:text-gray-400">{$i18n.t('New Password')}</div>
						<input
							class="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2.5 text-sm text-gray-900 dark:text-gray-100 outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
							type="password"
							bind:value={_user.password}
							autocomplete="new-password"
						/>
					</div>
				</div>

				<div class="mt-4 flex flex-row items-center justify-end gap-2 text-sm font-medium">
					<button
						type="button"
						class="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors shadow-sm"
						on:click={() => {
							show = false;
						}}
					>
						{$i18n.t('Cancel')}
					</button>
					<button
						class="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 text-white transition-colors shadow-sm"
						type="submit"
					>
						{$i18n.t('Save')}
					</button>
				</div>
			</form>
		{/if}
	</div>
</Modal>

