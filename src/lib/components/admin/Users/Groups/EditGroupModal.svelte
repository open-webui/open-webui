<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import General from './General.svelte';
	import Permissions from './Permissions.svelte';
	import Users from './Users.svelte';
	import UserPlusSolid from '$lib/components/icons/UserPlusSolid.svelte';
	import WrenchSolid from '$lib/components/icons/WrenchSolid.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let onSubmit: Function = () => {};
	export let onDelete: Function = () => {};

	export let show = false;
	export let edit = false;

	export let group = null;
	export let defaultPermissions = {};

	export let custom = true;

	export let tabs = ['general', 'permissions', 'users'];

	let selectedTab = 'general';
	let loading = false;
	let showDeleteConfirmDialog = false;

	let userCount = 0;

	export let name = '';
	export let description = '';
	export let data = {};

	export let permissions = {
		workspace: {
			models: false,
			knowledge: false,
			prompts: false,
			tools: false,
			models_import: false,
			models_export: false,
			prompts_import: false,
			prompts_export: false,
			tools_import: false,
			tools_export: false
		},
		sharing: {
			models: false,
			public_models: false,
			knowledge: false,
			public_knowledge: false,
			prompts: false,
			public_prompts: false,
			tools: false,
			public_tools: false,
			notes: false,
			public_notes: false
		},
		chat: {
			controls: true,
			valves: true,
			system_prompt: true,
			params: true,
			file_upload: true,
			delete: true,
			delete_message: true,
			continue_response: true,
			regenerate_response: true,
			rate_response: true,
			edit: true,
			share: true,
			export: true,
			stt: true,
			tts: true,
			call: true,
			multiple_models: true,
			temporary: true,
			temporary_enforced: false
		},
		features: {
			api_keys: false,
			notes: true,
			channels: true,
			folders: true,
			direct_tool_servers: false,
			web_search: true,
			image_generation: true,
			code_interpreter: true
		}
	};

	const submitHandler = async () => {
		loading = true;

		const group = {
			name,
			description,
			data,
			permissions
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
			data = group?.data ?? {};

			userCount = group?.member_count ?? 0;
		}
	};

	$: if (show) {
		init();
	}

	onMount(() => {
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

<Modal size="lg" bind:show>
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
				}}
			>
				<XMark className={'size-5'} />
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
									<div class=" self-center">{$i18n.t('Permissions')}</div>
								</button>
							{/if}

							{#if tabs.includes('users')}
								<button
									class="px-0.5 py-1 max-w-fit w-fit rounded-lg flex-1 lg:flex-none flex text-right transition {selectedTab ===
									'users'
										? ''
										: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
									on:click={() => {
										selectedTab = 'users';
									}}
									type="button"
								>
									<div class=" self-center mr-2">
										<UserPlusSolid />
									</div>
									<div class=" self-center">{$i18n.t('Users')}</div>
								</button>
							{/if}
						</div>

						<div class="flex-1 mt-1 lg:mt-1 lg:h-[30rem] lg:max-h-[30rem] flex flex-col">
							<div class="w-full h-full overflow-y-auto scrollbar-hidden">
								{#if selectedTab == 'general'}
									<General
										bind:name
										bind:description
										bind:data
										{edit}
										onDelete={() => {
											showDeleteConfirmDialog = true;
										}}
									/>
								{:else if selectedTab == 'permissions'}
									<Permissions bind:permissions {defaultPermissions} />
								{:else if selectedTab == 'users'}
									<Users bind:userCount groupId={group?.id} />
								{/if}
							</div>

							{#if ['general', 'permissions'].includes(selectedTab)}
								<div class="flex justify-end pt-3 text-sm font-medium gap-1.5">
									<button
										class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center {loading
											? ' cursor-not-allowed'
											: ''}"
										type="submit"
										disabled={loading}
									>
										{$i18n.t('Save')}

										{#if loading}
											<div class="ml-2 self-center">
												<Spinner />
											</div>
										{/if}
									</button>
								</div>
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
				</form>
			</div>
		</div>
	</div>
</Modal>
