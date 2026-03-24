<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher } from 'svelte';
	import { onMount, getContext } from 'svelte';
	import { addUser } from '$lib/apis/auths';

	import { WEBUI_BASE_URL } from '$lib/constants';

	import Modal from '$lib/components/common/Modal.svelte';

	const i18n: any = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;

	let loading = false;
	let tab = '';
	let inputFiles;

	let _user = {
		name: '',
		email: '',
		password: '',
		role: 'user'
	};

	$: if (show) {
		_user = {
			name: '',
			email: '',
			password: '',
			role: 'user'
		};
	}

	const submitHandler = async () => {
		const stopLoading = () => {
			dispatch('save');
			loading = false;
		};

		if (tab === '') {
			loading = true;

			const res = await addUser(
				localStorage.token,
				_user.name,
				_user.email,
				_user.password,
				_user.role
			).catch((error) => {
				toast.error(`${error}`);
			});

			if (res) {
				stopLoading();
				show = false;
			}
		} else {
			if (inputFiles) {
				loading = true;

				const file = inputFiles[0];
				const reader = new FileReader();

				reader.onload = async (e) => {
					const csv = e.target.result;
					const rows = csv.split('\n');

					let userCount = 0;

					for (const [idx, row] of rows.entries()) {
						const columns = row.split(',').map((col) => col.trim());
						console.log(idx, columns);

						if (idx > 0) {
							if (
								columns.length === 4 &&
								['admin', 'user', 'pending'].includes(columns[3].toLowerCase())
							) {
								const res = await addUser(
									localStorage.token,
									columns[0],
									columns[1],
									columns[2],
									columns[3].toLowerCase()
								).catch((error) => {
									toast.error(`Row ${idx + 1}: ${error}`);
									return null;
								});

								if (res) {
									userCount = userCount + 1;
								}
							} else {
								toast.error(`Row ${idx + 1}: invalid format.`);
							}
						}
					}

					toast.success(`Successfully imported ${userCount} users.`);
					inputFiles = null;
					const uploadInputElement = document.getElementById('upload-user-csv-input');

					if (uploadInputElement) {
						uploadInputElement.value = null;
					}

					stopLoading();
				};

				reader.readAsText(file);
			} else {
				toast.error($i18n.t('File not found.'));
			}
		}

		loading = false;
	};
</script>

<Modal
	size="sm"
	bind:show
	backdropClassName="bg-black/20 backdrop-blur-[1px] dark:bg-black/35"
>
	<div class="bg-white dark:bg-gray-900 rounded-xl">
		<!-- Header -->
		<div class="flex items-center justify-between px-6 py-5 border-b border-gray-200 dark:border-gray-700">
			<div class="flex items-center gap-3">
				<div class="p-2.5 bg-blue-50 dark:bg-blue-900/20 rounded-xl">
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 text-blue-600 dark:text-blue-400">
						<path stroke-linecap="round" stroke-linejoin="round" d="M19 7.5v3m0 0v3m0-3h3m-3 0h-3m-2.25-4.125a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zM4 19.235v-.11a6.375 6.375 0 0112.75 0v.109A12.318 12.318 0 0110.374 21c-2.331 0-4.512-.645-6.374-1.766z" />
					</svg>
				</div>
				<div>
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white">
						{$i18n.t('Add User')}
					</h2>
					<p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
						Create a new user account
					</p>
				</div>
			</div>
			<button
				class="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
				on:click={() => {
					show = false;
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5 text-gray-500 dark:text-gray-400"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>

		<!-- Form Content -->
		<form
			class="p-6"
			on:submit|preventDefault={() => {
				submitHandler();
			}}
		>
			<!-- Tabs -->
			<div class="flex gap-1 p-1 mb-5 bg-gray-100 dark:bg-gray-800 rounded-lg">
				<button
					class="flex-1 px-4 py-2.5 text-sm font-medium rounded-md transition-all {tab === ''
						? 'bg-white dark:bg-gray-900 text-gray-900 dark:text-white shadow-sm'
						: 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'}"
					type="button"
					on:click={() => {
						tab = '';
					}}
				>
					<div class="flex items-center justify-center gap-2">
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
						</svg>
						{$i18n.t('Form')}
					</div>
				</button>

				<button
					class="flex-1 px-4 py-2.5 text-sm font-medium rounded-md transition-all {tab === 'import'
						? 'bg-white dark:bg-gray-900 text-gray-900 dark:text-white shadow-sm'
						: 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'}"
					type="button"
					on:click={() => {
						tab = 'import';
					}}
				>
					<div class="flex items-center justify-center gap-2">
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
						</svg>
						{$i18n.t('CSV Import')}
					</div>
				</button>
			</div>

			<!-- Form Fields -->
			{#if tab === ''}
				<div class="space-y-4">
					<!-- Role Field -->
					<div class="space-y-2">
						<label for="user-role" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
							{$i18n.t('Role')}
							<span class="text-red-500">*</span>
						</label>
						<div class="relative">
							<div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
								<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 text-gray-400">
									<path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
								</svg>
							</div>
							<select
								id="user-role"
								class="w-full pl-10 pr-4 py-2.5 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white capitalize focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent outline-none transition-all"
								bind:value={_user.role}
								placeholder={$i18n.t('Enter Your Role')}
								required
							>
								<option value="pending"> {$i18n.t('pending')} </option>
								<option value="user"> {$i18n.t('user')} </option>
								<option value="admin"> {$i18n.t('admin')} </option>
							</select>
						</div>
					</div>

					<!-- Name Field -->
					<div class="space-y-2">
						<label for="user-name" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
							{$i18n.t('Name')}
							<span class="text-red-500">*</span>
						</label>
						<div class="relative">
							<div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
								<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 text-gray-400">
									<path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
								</svg>
							</div>
							<input
								id="user-name"
								class="w-full pl-10 pr-4 py-2.5 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent outline-none transition-all"
								type="text"
								bind:value={_user.name}
								placeholder={$i18n.t('Enter Your Full Name')}
								autocomplete="off"
								required
							/>
						</div>
					</div>

					<!-- Email Field -->
					<div class="space-y-2">
						<label for="user-email" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
							{$i18n.t('Email')}
							<span class="text-red-500">*</span>
						</label>
						<div class="relative">
							<div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
								<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 text-gray-400">
									<path stroke-linecap="round" stroke-linejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
								</svg>
							</div>
							<input
								id="user-email"
								class="w-full pl-10 pr-4 py-2.5 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent outline-none transition-all"
								type="email"
								bind:value={_user.email}
								placeholder={$i18n.t('Enter Your Email')}
								required
							/>
						</div>
					</div>

					<!-- Password Field -->
					<div class="space-y-2">
						<label for="user-password" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
							{$i18n.t('Password')}
						</label>
						<div class="relative">
							<div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
								<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 text-gray-400">
									<path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
								</svg>
							</div>
							<input
								id="user-password"
								class="w-full pl-10 pr-4 py-2.5 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent outline-none transition-all"
								type="password"
								bind:value={_user.password}
								placeholder={$i18n.t('Enter Your Password')}
								autocomplete="off"
							/>
						</div>
					</div>
				</div>
			{:else if tab === 'import'}
				<div class="space-y-4">
					<!-- File Upload Area -->
					<div>
						<input
							id="upload-user-csv-input"
							hidden
							bind:files={inputFiles}
							type="file"
							accept=".csv"
						/>

						<button
							class="w-full p-8 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl hover:border-blue-500 dark:hover:border-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/10 transition-all group"
							type="button"
							on:click={() => {
								document.getElementById('upload-user-csv-input')?.click();
							}}
						>
							<div class="flex flex-col items-center gap-3">
								<div class="p-3 bg-gray-100 dark:bg-gray-800 group-hover:bg-blue-100 dark:group-hover:bg-blue-900/20 rounded-xl transition-colors">
									<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-8 h-8 text-gray-400 group-hover:text-blue-500 dark:group-hover:text-blue-400 transition-colors">
										<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m6.75 12l-3-3m0 0l-3 3m3-3v6m-1.5-15H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
									</svg>
								</div>
								<div class="text-center">
									{#if inputFiles}
										<p class="text-sm font-medium text-gray-900 dark:text-white">
											{inputFiles.length} {inputFiles.length === 1 ? 'file' : 'files'} selected
										</p>
										<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
											{inputFiles[0].name}
										</p>
									{:else}
										<p class="text-sm font-medium text-gray-900 dark:text-white">
											{$i18n.t('Click here to select a csv file.')}
										</p>
										<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
											CSV files only
										</p>
									{/if}
								</div>
							</div>
						</button>
					</div>

					<!-- Info Box -->
					<div class="p-4 bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800 rounded-lg">
						<div class="flex gap-3">
							<div class="flex-shrink-0">
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5 text-blue-600 dark:text-blue-400">
									<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clip-rule="evenodd" />
								</svg>
							</div>
							<div class="flex-1 text-sm text-gray-700 dark:text-gray-300 space-y-2">
								<p class="font-medium">CSV Format Requirements:</p>
								<p>
									{$i18n.t('Ensure your CSV file includes 4 columns in this order: Name, Email, Password, Role.')}
								</p>
								<a
									class="inline-flex items-center gap-1.5 text-blue-600 dark:text-blue-400 hover:underline font-medium"
									href="{WEBUI_BASE_URL}/static/user-import.csv"
								>
									<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
										<path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
									</svg>
									{$i18n.t('Click here to download user import template file.')}
								</a>
							</div>
						</div>
					</div>
				</div>
			{/if}

			<!-- Footer Actions -->
			<div class="flex items-center justify-end gap-3 mt-6 pt-5 border-t border-gray-200 dark:border-gray-700">
				<button
					type="button"
					class="px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
					on:click={() => {
						show = false;
					}}
					disabled={loading}
				>
					{$i18n.t('Cancel')}
				</button>
				<button
					class="px-6 py-2.5 text-sm font-medium bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 text-white rounded-lg transition-colors shadow-sm flex items-center gap-2 {loading
						? 'opacity-50 cursor-not-allowed'
						: ''}"
					type="submit"
					disabled={loading}
				>
					{#if loading}
						<svg
							class="w-4 h-4 animate-spin"
							viewBox="0 0 24 24"
							fill="currentColor"
							xmlns="http://www.w3.org/2000/svg"
						>
							<style>
								.spinner_ajPY {
									transform-origin: center;
									animation: spinner_AtaB 0.75s infinite linear;
								}
								@keyframes spinner_AtaB {
									100% {
										transform: rotate(360deg);
									}
								}
							</style>
							<path
								d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z"
								opacity=".25"
							/>
							<path
								d="M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z"
								class="spinner_ajPY"
							/>
						</svg>
						{$i18n.t('Saving...')}
					{:else}
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
						</svg>
						{$i18n.t('Save')}
					{/if}
				</button>
			</div>
		</form>
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