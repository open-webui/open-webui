<script lang="ts">
	import { getContext } from 'svelte';
	import { onClickOutside } from '$lib/utils';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import { updateUserRole, getUsers, deleteUserById } from '$lib/apis/users';
	import Pagination from '$lib/components/common/Pagination.svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import InviteMenu from './InviteMenu.svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	export let users = [];
	let page = 1;

	$: console.log(users, 'users');

	let invitedEmails: string[] = [];

	let input = '';
	let inputRef: HTMLInputElement;

	let search = '';

	let filteredUsers;

	$: filteredUsers = users
		.filter((user) => {
			if (search === '') {
				return true;
			} else {
				let fullName = `${user.first_name.toLowerCase()} ${user.last_name.toLowerCase()}`;
				const query = search.toLowerCase();
				return fullName?.includes(query);
			}
		})
		.slice((page - 1) * 20, page * 20);

	const isValidEmail = (email: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());

	function addEmail() {
		const email = input.trim().toLowerCase();
		if (email && isValidEmail(email) && !invitedEmails.includes(email)) {
			invitedEmails = [...invitedEmails, email];
			input = '';
		}
	}

	function removeEmail(email: string) {
		invitedEmails = invitedEmails.filter((e) => e !== email);
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' || event.key === ',') {
			event.preventDefault();
			addEmail();
		} else if (event.key === 'Backspace' && input === '') {
			invitedEmails = invitedEmails.slice(0, -1);
		}
	}

	const emailColors = ['#272A6A', '#044B49', '#2F074F', '#27456A', '#0C2E18', '#47074F', '#6A2738'];
	let emailFocused = false;

	let showUsersRoleDropdown = false;
	let usersRoleRef;
	let roles = ['user', 'admin'];
	let selectedRole = roles[0];

	const updateRoleHandler = async (id, role) => {
		const res = await updateUserRole(localStorage.token, id, role).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			users = await getUsers(localStorage.token);
		}
	};
</script>

<div>
	<div
		class="flex w-full justify-between items-center py-2.5 border-b border-customGray-700 mb-2.5"
	>
		<div class="flex w-full justify-between items-center">
			<div class="text-xs dark:text-customGray-300">{$i18n.t('Member Management')}</div>
		</div>
	</div>
	<form
		class="flex flex-col self-center dark:bg-customGray-800 rounded-2xl w-full"
		on:submit={(e) => {
			e.preventDefault();
			inviteHandler();
		}}
	>
		<div
			class="bg-white relative dark:bg-customGray-900 rounded-md mb-2.5"
			style="min-height: 82px;"
		>
			{#if invitedEmails?.length < 1 && !emailFocused}
				<div
					class="absolute left-2.5 text-sm top-2.5 dark:text-customGray-100 dark:bg-customGray-900 pointer-events-none"
				>
					{$i18n.t('Send invites to')}
				</div>
				<span
					class="absolute top-[26px] w-[14rem] text-right right-2.5 -translate-y-1/2 text-xs dark:text-customGray-100/50 pointer-events-none select-none"
				>
					example@email.com, example@email, comexample@email.com
				</span>
			{/if}
			<div class="flex flex-wrap gap-1 items-start p-3" on:click={() => inputRef.focus()}>
				{#each invitedEmails as email, index (email)}
					<div
						style={`background-color: ${emailColors[index % emailColors.length]}`}
						class="flex items-start text-xs px-2 py-1 rounded-full dark:text-white"
					>
						{email}
						<button
							type="button"
							class="ml-1 text-xs font-bold hover:text-red-500"
							on:click={() => removeEmail(email)}
						>
							×
						</button>
					</div>
				{/each}

				<input
					bind:this={inputRef}
					bind:value={input}
					placeholder="Enter email..."
					class="text-xs bg-transparent outline-none px-1 h-6 w-auto max-w-[150px]"
					on:keydown={handleKeydown}
					on:blur={() => {
						addEmail();
						emailFocused = false;
					}}
					on:focus={() => (emailFocused = true)}
				/>
			</div>
		</div>
		<span class="text-xs dark:text-customGray-100/50 mb-5"
			>{$i18n.t('Separate multiple email addresses with commas.')}</span
		>
		<div class="flex w-full items-center justify-between">
			<div class="flex-1 mr-2.5" use:onClickOutside={() => (showUsersRoleDropdown = false)}>
				<div class="relative" bind:this={usersRoleRef}>
					<button
						type="button"
						class="flex items-center justify-between w-full text-sm {selectedRole
							? 'h-12'
							: 'h-10'} px-3 py-2 {showUsersRoleDropdown
							? 'border'
							: ''} border-gray-300 dark:border-customGray-700 rounded-md bg-white dark:bg-customGray-900 cursor-pointer"
						on:click={() => (showUsersRoleDropdown = !showUsersRoleDropdown)}
					>
						<span class="text-gray-500 dark:text-customGray-100">{$i18n.t('User Permissions')}</span
						>
						<div class="flex items-center">
							<div class="text-xs dark:text-customGray-100/50 max-w-[15rem] text-left">
								{#if selectedRole === "user"}
									<span class="bg-[#024D15] rounded-lg text-xs text-[#0F8C18] px-2 w-fit">{$i18n.t('User')}</span>
								{:else}
									<span class="bg-[#33176E] rounded-lg text-xs text-[#7147CD] px-2 w-fit">{$i18n.t('Admin')}</span>
								{/if}
							</div>
							<ChevronDown className="size-3 ml-1" />
						</div>
					</button>

					{#if showUsersRoleDropdown}
						<div
							class="max-h-60 pb-1 overflow-y-auto absolute z-50 w-full -mt-1 bg-white dark:bg-customGray-900 border-l border-r border-b border-gray-300 dark:border-customGray-700 rounded-b-md shadow"
						>
							<hr class="border-t border-customGray-700 mb-2 mt-1 mx-0.5" />
							<div class="px-1">
								{#each roles as role}
									<div
										role="button"
										tabindex="0"
										on:click={() => {
											selectedRole = role;
											showUsersRoleDropdown = false;
										}}
										class="flex items-center rounded-xl w-full justify-between px-3 py-2 hover:bg-gray-100 dark:hover:bg-customGray-950 cursor-pointer text-sm dark:text-customGray-100"
									>
										<div class="flex items-center gap-2">
											{#if role === "user"}
												<span class="bg-[#024D15] rounded-lg text-xs text-[#0F8C18] px-2 w-fit">{$i18n.t('User')}</span>
											{:else}
												<span class="bg-[#33176E] rounded-lg text-xs text-[#7147CD] px-2 w-fit">{$i18n.t('Admin')}</span>
											{/if}
										</div>
									</div>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			</div>
			<button
				class="bg-gray-900 text-xs dark:bg-customGray-900 border dark:border-customGray-700 dark:hover:bg-customGray-950 text-gray-100 dark:text-customGray-200 py-2.5 px-4 h-12 rounded-lg transition"
				on:click={() => {}}
				type="button"
			>
				{$i18n.t('Send invites')}
			</button>
		</div>
	</form>
	<div class="flex justify-end mt-5 mb-1">
		<div class="flex w-[12rem] border dark:border-customGray-700 rounded-lg dark:bg-customGray-900 dark:text-customGray-200">
			<div class=" self-center ml-4 mr-2">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-3 h-3"
				>
					<path
						fill-rule="evenodd"
						d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
						clip-rule="evenodd"
					/>
				</svg>
			</div>
			<input
				class=" w-full text-xs pr-4 py-1 rounded-r-xl outline-none bg-transparent h-[30px]"
				bind:value={search}
				placeholder={$i18n.t('Search')}
			/>
		</div>
	</div>

	<div
		class="flex w-full justify-between items-center py-2.5 border-b border-customGray-700 mb-2.5"
	>
		<div class="flex w-full justify-start items-center">
			<div class="text-xs dark:text-customGray-300 w-[calc(55%+8px)]">{$i18n.t('Users')}</div>
			<div class="text-xs dark:text-customGray-300">{$i18n.t('Roles')}</div>
		</div>
	</div>
	
	{#each filteredUsers as user, userIdx}
		<div class="grid grid-cols-[55%_60px_1fr_26px] gap-x-2 mb-[14px] group cursor-pointer">
			<div class="flex items-center">
				<img
					class=" rounded-full w-3 h-3 object-cover mr-2.5"
					src={user.profile_image_url.startsWith(WEBUI_BASE_URL) ||
					user.profile_image_url.startsWith('https://www.gravatar.com/avatar/') ||
					user.profile_image_url.startsWith('data:')
						? user.profile_image_url
						: `/user.png`}
					alt="user"
				/>
				{#if (user?.first_name !== 'INVITED')}
					<div class="text-xs dark:text-customGray-100 mr-1 whitespace-nowrap">{user.first_name} {user.last_name}</div>
				{/if}
				<div class="text-xs dark:text-customGray-590 mr-1 whitespace-nowrap">{user.email}</div>
			</div>
			<div>
				<button
					class="flex"
					on:click={() => {
						if (user.role === 'user') {
							updateRoleHandler(user.id, 'admin');
						}  else {
							updateRoleHandler(user.id, 'user');
						}
					}}
				>
					{#if user.role === "user"}
						<span class="bg-[#024D15] rounded-lg text-xs text-[#0F8C18] px-2 w-fit">{$i18n.t('User')}</span>
					{:else}
						<span class="bg-[#33176E] rounded-lg text-xs text-[#7147CD] px-2 w-fit">{$i18n.t('Admin')}</span>
					{/if}
				</button>
			</div>
			<div>
				{#if (user?.first_name === 'INVITED')}
					<div class="self-center rounded-lg text-xs px-2 w-fit whitespace-nowrap bg-[#113272] text-[#3F70CF]">Invite pending</div>
				{/if}
			</div>
			{#if (user?.first_name === 'INVITED')}
				<div class="invisible group-hover:visible h-4">
					<InviteMenu
						editHandler={async () => {
						}}
						deleteHandler={async () => {
							
						}}
						onClose={() => {}}
					>
						<button
							class="self-center w-fit text-sm px-0.5 h-[21px] dark:text-white dark:hover:text-white hover:bg-black/5 dark:hover:bg-customGray-900 rounded-md"
							type="button"
							on:click={(e) => {}}
						>
							<EllipsisHorizontal className="size-5" />
						</button>
					</InviteMenu>
				</div>
			{:else}
				<div></div>
			{/if}
		</div>
	{/each}
</div>
