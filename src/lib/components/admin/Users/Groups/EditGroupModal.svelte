<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import Modal from '$lib/components/common/Modal.svelte';
	import Display from './Display.svelte';
	import Permissions from './Permissions.svelte';
	import Users from './Users.svelte';
	import UserPlusSolid from '$lib/components/icons/UserPlusSolid.svelte';
	import WrenchSolid from '$lib/components/icons/WrenchSolid.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	export let onSubmit: Function = () => {};
	export let onDelete: Function = () => {};

	export let show = false;
	export let edit = false;

	export let users = [];
	export let group = null;

	export let custom = true;

	export let tabs = ['general', 'permissions', 'users'];

	let selectedTab = 'general';
	let loading = false;
	let showDeleteConfirmDialog = false;

	export let name = '';
	export let description = '';

	export let permissions = {
		workspace: {
			models: false,
			knowledge: false,
			prompts: false,
			tools: false
		},
		sharing: {
			public_models: false,
			public_knowledge: false,
			public_prompts: false,
			public_tools: false
		},
		chat: {
			controls: true,
			file_upload: true,
			delete: true,
			edit: true,
			temporary: true
		},
		features: {
			direct_tool_servers: false,
			web_search: true,
			image_generation: true,
			code_interpreter: true
		}
	};
	export let userIds = [];

	const submitHandler = async () => {
		loading = true;

		const group = {
			name,
			description,
			permissions,
			user_ids: userIds
		};

		await onSubmit(group);

		loading = false;
		show = false;
	};

	const init = () => {
		if (group) {
			name = group.name;
			description = group.description;
			permissions = group?.permissions ?? {};

			userIds = group?.user_ids ?? [];
		}
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

<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	on:confirm={() => {
		onDelete();
		show = false;
	}}
/>

<Modal
	size="md"
	bind:show
	backdropClassName="bg-black/20 backdrop-blur-[1px] dark:bg-black/35"
>
	<div class="rounded-2xl overflow-hidden bg-white dark:bg-gray-900 max-h-[88dvh] flex flex-col">
		<div class="flex items-center justify-between border-b border-gray-200 dark:border-gray-800 px-4 sm:px-5 py-3.5 sm:py-4 shrink-0">
			<div class="text-base sm:text-lg font-semibold text-gray-900 dark:text-gray-100 font-primary pr-2">
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
				class="inline-flex items-center justify-center rounded-lg p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200 transition-colors"
				on:click={() => {
					show = false;
				}}
				aria-label="Close"
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

		<div class="flex flex-col md:flex-row w-full px-3 sm:px-4 pb-3 sm:pb-4 pt-3 md:space-x-4 dark:text-gray-200 min-h-0 flex-1 overflow-hidden">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full min-h-0"
					on:submit={(e) => {
						e.preventDefault();
						submitHandler();
					}}
				>
					<div class="flex flex-col lg:flex-row w-full h-full pb-2 lg:space-x-4 min-h-0">
						<div
							id="admin-settings-tabs-container"
							class="tabs flex w-full flex-wrap gap-2 max-w-full lg:gap-1.5 lg:flex-col lg:flex-none lg:w-44 lg:p-2 lg:rounded-xl lg:bg-gray-50 lg:dark:bg-gray-800/60 dark:text-gray-200 text-sm font-medium text-left"
						>
							{#if tabs.includes('general')}
								<button
									class="h-11 px-3 py-2 rounded-lg flex-1 min-w-[7rem] lg:min-w-0 lg:w-full lg:max-w-none lg:flex-none flex justify-center lg:justify-start items-center transition-colors {selectedTab ===
									'general'
										? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
										: 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700/60 hover:text-gray-700 dark:hover:text-gray-200'}"
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
									<div class="self-center whitespace-nowrap">{$i18n.t('General')}</div>
								</button>
							{/if}

							{#if tabs.includes('permissions')}
								<button
									class="h-11 px-3 py-2 rounded-lg flex-1 min-w-[7rem] lg:min-w-0 lg:w-full lg:max-w-none lg:flex-none flex justify-center lg:justify-start items-center transition-colors {selectedTab ===
									'permissions'
										? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
										: 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700/60 hover:text-gray-700 dark:hover:text-gray-200'}"
									on:click={() => {
										selectedTab = 'permissions';
									}}
									type="button"
								>
									<div class=" self-center mr-2">
										<WrenchSolid />
									</div>
									<div class="self-center whitespace-nowrap">{$i18n.t('Permissions')}</div>
								</button>
							{/if}

							{#if tabs.includes('users')}
								<button
									class="h-11 px-3 py-2 rounded-lg flex-1 min-w-[7rem] lg:min-w-0 lg:w-full lg:max-w-none lg:flex-none flex justify-center lg:justify-start items-center transition-colors {selectedTab ===
									'users'
										? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
										: 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700/60 hover:text-gray-700 dark:hover:text-gray-200'}"
									on:click={() => {
										selectedTab = 'users';
									}}
									type="button"
								>
									<div class=" self-center mr-2">
										<UserPlusSolid />
									</div>
									<div class="self-center whitespace-nowrap">{$i18n.t('Users')} ({userIds.length})</div>
								</button>
							{/if}
						</div>

						<div
							class="flex-1 min-h-0 mt-2 lg:mt-1 lg:h-[22rem] lg:max-h-[22rem] overflow-y-auto scrollbar-hidden rounded-xl border border-gray-200 dark:border-gray-800 bg-gray-50/70 dark:bg-gray-900/50 p-3"
						>
							{#if selectedTab == 'general'}
								<Display bind:name bind:description />
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
									: 'border-transparent text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
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
									: 'border-transparent text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
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
									: ' border-transparent text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
								on:click={() => {
									selectedTab = 'users';
								}}
								type="button"
							>
								{$i18n.t('Users')} ({userIds.length})
							</button>
						{/if}
					</div> -->

					<div class="flex justify-end items-center pt-3 sm:pt-4 mt-1 border-t border-gray-200 dark:border-gray-800 text-sm font-medium gap-2 shrink-0 bg-white/95 dark:bg-gray-900/95 backdrop-blur-sm">
						{#if edit}
							<button
								class="px-4 py-1.5 text-xs font-medium border border-gray-300 text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800 transition rounded-lg flex flex-row justify-center space-x-1 items-center"
								type="button"
								on:click={() => {
									showDeleteConfirmDialog = true;
								}}
							>
								{$i18n.t('Delete')}
							</button>
						{/if}

						<button
							class="px-4 py-1.5 text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white dark:bg-blue-500 dark:hover:bg-blue-600 transition rounded-lg shadow-sm flex flex-row justify-center space-x-1 items-center {loading
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
</Modal>
