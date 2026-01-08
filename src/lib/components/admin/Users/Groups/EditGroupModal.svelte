<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	import dayjs from 'dayjs';
	const i18n = getContext('i18n');

	import Modal from '$lib/components/common/Modal.svelte';
	import Display from './Display.svelte';
	import Permissions from './Permissions.svelte';
	import Users from './Users.svelte';
	import UserPlusSolid from '$lib/components/icons/UserPlusSolid.svelte';
	import WrenchSolid from '$lib/components/icons/WrenchSolid.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';

	export let onSubmit: Function = () => {};
	export let onDelete: Function = () => {};

	export let show = false;
	export let edit = false;

	export let users = [];
	export let group = null;


	export let custom = true;

	let showImportModal = false;
	let inputFiles;

	export let tabs = ['general', 'permissions', 'users'];

	let selectedTab = 'general';
	let loading = false;
	let showConfirmDelete = false;

	export let name = '';
	export let description = '';
	export let created_by = ''; // add creator name
	export let created_at = ''; // add creator initialization
	export let updated_at = ''; // add updated initialization

	export let co_admin_user_ids: string[] = [];
	export let co_admin_emails: string[] = [];


	export let permissions = {
		workspace: {
			models: false,
			knowledge: false,
			prompts: false,
			tools: false
		},
		chat: {
			controls: true,
			file_upload: true,
			delete: true,
			edit: true,
			temporary: true
		},
		features: {
			web_search: true,
			image_generation: true,
			code_interpreter: true
		}
	};
export let userIds = [];
// Keep co-admin list in sync with current members and users
$: {
	try {
		const memberUsers = (userIds || [])
			.map((id) => (users || []).find((u) => u.id === id))
			.filter((u) => !!u);
		co_admin_emails = memberUsers
			.filter((u) => u.role === 'admin' && (u.info?.is_co_admin === true))
			.map((u) => u.email);
	} catch (e) {
		// noop: keep previous value if any transient error
	}
}

	const submitHandler = async () => {
		loading = true;

		const group = {
			name,
			description,
			permissions,
			user_ids: userIds

			// Currently no need to add creator name here
		};

		await onSubmit(group);

		loading = false;
		show = false;
	};

	function handleImportCSV_temp(event) {
		const file = event.target.files[0];
		if (!file) return;

		if (file.size > 10 * 1024 * 1024) {
			console.error('File is too large (max 10MB)');
			return;
		}

		const reader = new FileReader();
		reader.onload = (e) => {
			const text = e.target.result;
			const lines = text.split(/\r?\n/).slice(0, 3);
		};
		reader.readAsText(file);
	}

	// Copied from src/lib/components/admin/Users/UserList.svelte
	// Also used in src/lib/components/admin/Users/Groups/Users.svelte for showing badge in EditGroupModal -> Users
	function getRoleLabel(user) {
		if (user.role === 'admin' && user.info?.is_co_admin) {
			return 'co-admin';
		}
		return user.role;
	}

	function handleImportCSV(event) {
		const file = event.target.files[0];
		if (!file) return;

		if (file.size > 10 * 1024 * 1024) {
			toast.error('File is too large (max 10MB)');
			return;
		}

		const reader = new FileReader();
		reader.onload = (e) => {
			try {
				const text = e.target.result;
				const lines = text.split(/\r?\n/).filter((line) => line.trim());

				// Extract emails (skip header if first line contains "Email")
				const startIndex = lines[0]?.toLowerCase().includes('email') ? 1 : 0;
				const csvEmails = lines
					.slice(startIndex)
					.map((line) => {
						return line.trim().toLowerCase();
					})
					.filter((email) => email && email.includes('@'));

				// Match emails to existing users and track which ones were found
				const matchedEmails = [];
				const newUserIds = users
					.filter((user) => {
						const isMatch = csvEmails.includes(user.email.toLowerCase());
						if (isMatch) {
							matchedEmails.push(user.email.toLowerCase());
						}
						return isMatch;
					})
					.map((user) => user.id)
					.filter((id) => !userIds.includes(id)); // Avoid duplicates

				// Find emails that couldn't be matched to existing users
				const unmatchedEmails = csvEmails.filter((email) => !matchedEmails.includes(email));

				if (newUserIds.length === 0) {
					if (unmatchedEmails.length > 0) {
						toast.error(
							`These ${unmatchedEmails.length} users: ${unmatchedEmails.join(', ')} could not be added to the group. The users are not onboarded to NYU Pilot GenAI yet.`
						);
					} else {
						toast.error('No new users to add (all users already in group)');
					}
					return;
				}

				// Add new user IDs to existing array
				userIds = [...userIds, ...newUserIds];

				// Show success message with details about partial failures
				const totalEmails = csvEmails.length;
				const successCount = newUserIds.length;

				if (unmatchedEmails.length > 0) {
					// Show individual error messages for unmatched emails
					// unmatchedEmails.forEach(email => {
					// 	toast.error(`Email not found: ${email}`);
					// });
					toast.error(
						`These ${unmatchedEmails.length} users: ${unmatchedEmails.join(', ')} could not be added to the group. The users are not onboarded to NYU Pilot GenAI yet.`
					);
					// Show success message with context
					toast.success(`Added ${successCount} of ${totalEmails} users to group`);
				} else {
					// All emails matched successfully
					toast.success(`Added ${successCount} users to group`);
				}

				showImportModal = false;
			} catch (error) {
				console.error('CSV parsing error:', error);
				toast.error('Error parsing CSV file');
			}
		};
		reader.readAsText(file);
	}

	function toDate(input) {
		// Accept number (seconds or ms) or numeric string or ISO string
		if (input == null) return null;

		// numeric value?
		const num = typeof input === 'number' ? input : Number(input);
		if (!Number.isNaN(num)) {
			// if value looks like seconds (rough heuristic: < 1e12) convert to ms
			const ms = num < 1e12 ? num * 1000 : num;
			return new Date(ms);
		}

		// fallback: parse as ISO/date string
		return new Date(input);
	}

	const init = () => {
		if (group) {
			name = group.name;
			description = group.description;
			permissions = group?.permissions ?? {};
			created_by = group?.created_by ?? 'Unknown';
			// user_ids_before_identify = group.user_ids
			
			const cDate = toDate(group?.created_at);
			created_at = cDate ? formatDateTime(cDate) : 'Unknown';

			const uDate = toDate(group?.updated_at);
			updated_at = uDate ? formatDateTime(uDate) : 'Unknown';

			// for relative display with dayjs:
			// dayjs(toDate(group.created_at)).fromNow()
			userIds = group?.user_ids ?? [];
		}
	};

	const formatDateTime = (input) => {
		// Handle different input types: Date object, timestamp in seconds, or timestamp in milliseconds
		let date;
		
		if (input instanceof Date) {
			// Already a Date object
			date = dayjs(input);
		} else if (typeof input === 'number') {
			// Timestamp - check if it's in seconds or milliseconds
			const timestamp = input < 1e12 ? input * 1000 : input;
			date = dayjs(timestamp);
		} else {
			// Fallback for other formats
			date = dayjs(input);
		}

		// Get timezone abbreviation using JavaScript
		const jsDate = date.toDate();
		const timezoneAbbr = jsDate.toLocaleTimeString('en-US', { timeZoneName: 'short' }).split(' ').pop();

		// Format: "Aug 18 2025, 04:05:15 PM (EST)"
		const formattedDate = date.format('MMM DD YYYY, hh:mm:ss A');
		
		return `${formattedDate} (${timezoneAbbr})`;
	};

	$: if (show) {
		init();
	}

	onMount(() => {
		console.log(tabs);
		selectedTab = tabs[0];
		init();
	});
</script>

<Modal size="md" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-100 px-5 pt-4 mb-1.5">
			<div class=" text-lg font-medium self-center font-primary">
				{#if custom}
					{#if edit}
						{$i18n.t('Edit User Group')}
					{:else}
						{$i18n.t('Add User Group')}
					{/if}
				{:else}
					{$i18n.t('Edit Default Permissions')}
				{/if}
			</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
					inputFiles = null;
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
										? 'text-[#57068c] dark:text-white'
										: ' text-gray-600 dark:text-gray-600 hover:text-[#57068c] dark:hover:text-white'}"
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
										? 'text-[#57068c] dark:text-white'
										: ' text-gray-600 dark:text-gray-600 hover:text-[#57068c] dark:hover:text-white'}"
									on:click={() => {
										selectedTab = 'permissions';
									}}
									type="button"
								>
									<div class=" self-center mr-2">
										<WrenchSolid />
									</div>
									<div class=" self-center">{$i18n.t('Permissions')}</div>
								</button>
							{/if}

							{#if tabs.includes('users')}
								<button
									class="px-0.5 py-1 max-w-fit w-fit rounded-lg flex-1 lg:flex-none flex text-right transition {selectedTab ===
									'users'
										? 'text-[#57068c] dark:text-white'
										: ' text-gray-600 dark:text-gray-600 hover:text-[#57068c] dark:hover:text-white'}"
									on:click={() => {
										selectedTab = 'users';
									}}
									type="button"
								>
									<div class=" self-center mr-2">
										<UserPlusSolid />
									</div>
									<div class=" self-center">{$i18n.t('Users')} ({userIds.length})</div>
									<!-- Entry of Users tab -->
								</button>
							{/if}
						</div>

						<div
							class="flex-1 mt-1 lg:mt-1 lg:h-[22rem] lg:max-h-[22rem] overflow-y-auto scrollbar-hidden"
						>
							{#if selectedTab == 'general'}
								<Display
									bind:name
									bind:description
									bind:created_by
									bind:created_at
									bind:updated_at
									{co_admin_emails}
								/>
								<!-- Finally put other stuff here -->
							{:else if selectedTab == 'permissions'}
								<Permissions bind:permissions />
							{:else if selectedTab == 'users'}
								<Users bind:userIds {users} />
							{/if}
						</div>
					</div>

					<!-- <div
						class=" tabs flex flex-row overflow-x-auto gap-2.5 text-sm font-medium border-b border-b-gray-800 scrollbar-hidden"
					>
						{#if tabs.includes('display')}
							<button
								class="px-0.5 pb-1.5 min-w-fit flex text-right transition border-b-2 {selectedTab ===
								'display'
									? ' dark:border-white'
									: 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-700 dark:hover:text-white'}"
								on:click={() => {
									selectedTab = 'display';
								}}
								type="button"
							>
								{$i18n.t('Display')}
							</button>
						{/if}

						{#if tabs.includes('permissions')}
							<button
								class="px-0.5 pb-1.5 min-w-fit flex text-right transition border-b-2 {selectedTab ===
								'permissions'
									? '  dark:border-white'
									: 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-700 dark:hover:text-white'}"
								on:click={() => {
									selectedTab = 'permissions';
								}}
								type="button"
							>
								{$i18n.t('Permissions')}
							</button>
						{/if}

						{#if tabs.includes('users')}
							<button
								class="px-0.5 pb-1.5 min-w-fit flex text-right transition border-b-2 {selectedTab ===
								'users'
									? ' dark:border-white'
									: ' border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-700 dark:hover:text-white'}"
								on:click={() => {
									selectedTab = 'users';
								}}
								type="button"
							>
								{$i18n.t('Users')} ({userIds.length})
							</button>
						{/if}
					</div> -->

					<div class="flex justify-end pt-3 text-sm font-medium gap-1.5">
						{#if selectedTab === 'users'}
							<button
								class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
								type="button"
								on:click={() => {
									showImportModal = true;
								}}
							>
								<div class="flex items-center text-gray-900 dark: text-gray-400">
									{$i18n.t('Import User List from CSV')}
								</div>
							</button>
						{/if}

						{#if edit}
							<button
								class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
								type="button"
								on:click={() => {
									showConfirmDelete = true;
								}}
							>
								<div class="flex items-center text-red-600">{$i18n.t('Delete')}</div>
							</button>
						{/if}

						<button
							class="px-4.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center {loading
								? ' cursor-not-allowed'
								: ''}"
							type="submit"
							disabled={loading}
						>
							{$i18n.t('Save')}

							{#if loading}
								<div class="ml-2 self-center">
									<svg
										class=" w-4 h-4"
										viewBox="0 0 24 24"
										fill="currentColor"
										xmlns="http://www.w3.org/2000/svg"
										><style>
											.spinner_ajPY {
												transform-origin: center;
												animation: spinner_AtaB 0.75s infinite linear;
											}
											@keyframes spinner_AtaB {
												100% {
													transform: rotate(360deg);
												}
											}
										</style><path
											d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z"
											opacity=".25"
										/><path
											d="M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z"
											class="spinner_ajPY"
										/></svg
									>
								</div>
							{/if}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>

	<ConfirmDialog
		bind:show={showConfirmDelete}
		title={$i18n.t('Delete Group')}
		message={$i18n.t('Are you sure you want to delete this group? This action cannot be undone.')}
		confirmLabel={$i18n.t('Delete')}
		cancelLabel={$i18n.t('Cancel')}
		onConfirm={() => {
			onDelete();
			show = false;
		}}
	/>
</Modal>

<!-- Import Modal -->
<Modal size="sm" bind:show={showImportModal}>
	<div>
		<div class="flex justify-between dark:text-gray-300 px-5 pt-4 pb-2">
			<div class="text-lg font-medium self-center">{$i18n.t('Import Users from CSV')}</div>
			<button
				class="self-center"
				on:click={() => {
					showImportModal = false;
					inputFiles = null;
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
		<div class="px-5 pb-4">
			<div class="mb-3 w-full">
				<input
					id="upload-user-csv-input"
					hidden
					bind:files={inputFiles}
					type="file"
					accept=".csv"
					on:change={handleImportCSV}
				/>
				<button
					class="w-full text-sm font-medium py-3 bg-transparent hover:bg-gray-100 border border-dashed dark:border-gray-850 dark:hover:bg-gray-850 text-center rounded-xl"
					type="button"
					on:click={() => {
						document.getElementById('upload-user-csv-input')?.click();
					}}
				>
					{#if inputFiles}
						{inputFiles.length > 0 ? `${inputFiles.length}` : ''} document(s) selected.
					{:else}
						{$i18n.t('Click here to select a csv file.')}
					{/if}
				</button>
			</div>
			<div class="text-xs text-gray-600 dark:text-gray-500">
				ⓘ {@html $i18n.t(
					'Upload a CSV file with one column named email. Each line should contain the NetID email address of a user you want to add to this group. Users must be <strong>already onboarded to NYU Pilot GenAI</strong> for them to be added to the group'
				)}
				<a
					class="underline dark:text-gray-200"
					href="{WEBUI_BASE_URL}/static/sample.csv"
					target="_blank"
					rel="noopener"
				>
					<br /> Here's a sample.csv file
				</a>
			</div>
		</div>
	</div>
</Modal>
