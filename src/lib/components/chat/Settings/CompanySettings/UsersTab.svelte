<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { onClickOutside } from '$lib/utils';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import { updateUserRole, getUsers, deleteUserById } from '$lib/apis/users';
	import Pagination from '$lib/components/common/Pagination.svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import InviteMenu from './InviteMenu.svelte';
	import { toast } from 'svelte-sonner';
	import { inviteUsers } from '$lib/apis/auths';
	import ChevronUpDown from '$lib/components/icons/ChevronUpDown.svelte';
	import GroupSelect from './GroupSelect.svelte';
	import { getGroups } from '$lib/apis/groups';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	const i18n = getContext('i18n');

	$: console.log(WEBUI_BASE_URL);

	export let users = [];
	export let getUsersHandler: Function;
	export let getSubscription: Function;
	let page = 1;

	$: console.log(users, 'users');

	let invitedEmails: string[] = [];

	let input = '';
	let inputRef: HTMLInputElement;
	let ghostRef;

	function updateInputWidth() {
		if (ghostRef && inputRef) {
			ghostRef.textContent = input || ' ';
			const width = ghostRef.offsetWidth + 10; 
			inputRef.style.width = `${width}px`;
		}
	}

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
	let openDropdownIdx = null;
	let selectedGroups = [];

	const updateRoleHandler = async (id, role) => {
		const res = await updateUserRole(localStorage.token, id, role).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			users = await getUsers(localStorage.token);
		}
	};

	const inviteUsersHandler = async () => {
		const invitees = invitedEmails.map((item) => ({ email: item, role: selectedRole }));
		const existingGroups = selectedGroups?.filter(group => group.id);
		const newGroups = selectedGroups?.filter(group => !group.id);
		const existingGroupsIds= existingGroups?.length > 0 ? existingGroups?.map(group => group.id) : null;
		const newGroupNames = newGroups?.length > 0 ? newGroups?.map(group => group.name) : null;
		const res = await inviteUsers(localStorage.token, invitees, existingGroupsIds, newGroupNames).catch((error) =>
			toast.error(`${error}`)
		);
		if (res?.success){
			toast.success($i18n.t('Invited successfuly'))
			getUsersHandler();
			getSubscription();
		} else {
			res?.failed_invites?.forEach(res => {
				toast.error(`${res.reason}`)
			})
		}
		
		invitedEmails = [];
		selectedGroups = []
	};
	let groups = [];
	const setGroups = async () => {
		groups = await getGroups(localStorage.token);
	};
	onMount(async () => {
		setGroups();
	});

	let showDeleteConfirm = false;
	let userToDelete = null;

	const deleteHandler = async (id) => {
		const res = await deleteUserById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('User deleted successfully'));
			getUsersHandler();
			getSubscription();
		}
	};

</script>

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete user?')}
	on:confirm={() => {
		deleteHandler(userToDelete?.id);
		userToDelete = null;
	}}
	on:cancel={() => {
		userToDelete = null;
	}}
>
<div class=" text-sm text-gray-500 flex-1 line-clamp-3">
	{$i18n.t('This will delete')} <span class="  font-semibold">{userToDelete?.email}</span>.
</div>
</DeleteConfirmDialog>

<div class="pb-24 min-h-[32rem]">
	<div
		class="flex w-full justify-between items-center py-2.5 border-b border-lightGray-400 dark:border-customGray-700 mb-2.5"
	>
		<div class="flex w-full justify-between items-center">
			<div class="text-xs text-lightGray-100 dark:text-customGray-300 font-medium">{$i18n.t('Member Management')}</div>
		</div>
	</div>
	<form
		class="flex flex-col self-center dark:bg-customGray-800 rounded-2xl w-full"
		on:submit={(e) => {
			e.preventDefault();
		}}
	>
		<div
			class="bg-lightGray-300 relative dark:bg-customGray-900 rounded-md mb-2.5"
			style="min-height: 82px;"
		>
			{#if invitedEmails?.length < 1 && !emailFocused}
				<div
					class="absolute left-2.5 text-sm top-2.5 bg-lightGray-300 text-lightGray-100 dark:text-customGray-100 dark:bg-customGray-900 pointer-events-none"
				>
					{$i18n.t('Send invites to')}
				</div>
				<span
					class="absolute top-[26px] w-[12rem] text-lightGray-100/50 text-right right-2.5 -translate-y-1/2 text-xs dark:text-customGray-100/50 pointer-events-none select-none"
				>
					Add Team member mails (separated by comma)
				</span>
			{/if}
			<div class="flex flex-wrap gap-1 items-start p-3" on:click={() => inputRef.focus()}>
				{#each invitedEmails as email, index (email)}
					<div
						style={`background-color: ${emailColors[index % emailColors.length]}`}
						class="flex items-start text-xs px-2 py-1 rounded-full text-white dark:text-white"
					>
						{email}
						<button
							type="button"
							class="ml-1 text-xs font-bold"
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
					class="text-xs bg-transparent outline-none px-1 h-6 min-w-[100px]"
					on:keydown={handleKeydown}
					on:blur={() => {
						addEmail();
						emailFocused = false;
					}}
					on:focus={() => (emailFocused = true)}
					on:input={updateInputWidth}
				/>
				<span bind:this={ghostRef} class="invisible absolute whitespace-pre text-xs px-1"></span>
			</div>
		</div>
		<span class="text-xs text-lightGray-100/50 dark:text-customGray-100/50 mb-5"
			>{$i18n.t('Separate multiple email addresses with commas.')}</span
		>

		<div class="w-full mb-2.5" use:onClickOutside={() => (showUsersRoleDropdown = false)}>
			<div class="relative" bind:this={usersRoleRef}>
				<button
					type="button"
					class="flex items-center justify-between w-full text-sm {selectedRole
						? 'h-12'
						: 'h-10'} px-3 py-2 {showUsersRoleDropdown
						? 'border'
						: ''} border-lightGray-400 dark:border-customGray-700 rounded-md bg-lightGray-300 dark:bg-customGray-900 cursor-pointer"
					on:click={() => (showUsersRoleDropdown = !showUsersRoleDropdown)}
				>
					<span class="text-lightGray-100 dark:text-customGray-100">{$i18n.t('User Permissions')}</span>
					<div class="flex items-center">
						<div class="text-xs dark:text-customGray-100/50 max-w-[15rem] text-left">
							{#if selectedRole === 'user'}
								<span class="bg-[#99C3A3] dark:bg-[#024D15] rounded-[9px] text-xs text-[#1D7732] dark:text-[#0F8C18] px-2 py-1 w-fit font-medium"
									>{$i18n.t('User')}</span
								>
							{:else}
								<span class="bg-[#A99EC2] text-[#5D4497] font-medium dark:bg-[#33176E] rounded-[9px] text-xs  dark:text-[#7147CD] px-2 py-1 w-fit"
									>{$i18n.t('Admin')}</span
								>
							{/if}
						</div>
						<ChevronDown className="size-3 ml-1 text-lightGray-100 dark:text-customGray-100" />
					</div>
				</button>

				{#if showUsersRoleDropdown}
					<div
						class="max-h-60 overflow-y-auto absolute top-10 right-4 z-50 bg-lightGray-300 dark:bg-customGray-900 border border-gray-300 dark:border-customGray-700 rounded-md shadow"
					>
						<div class="px-[6px] py-1">
							{#each roles as role}
								<div
									role="button"
									tabindex="0"
									on:click={() => {
										selectedRole = role;
										showUsersRoleDropdown = false;
									}}
									class="flex items-center justify-end rounded-xl w-full py-1 cursor-pointer text-sm dark:text-customGray-100"
								>
									<div class="flex items-center">
										{#if role === 'user'}
											<span class="bg-[#99C3A3] dark:bg-[#024D15] rounded-[9px] py-[3px] text-xs text-[#1D7732] dark:text-[#0F8C18] px-2 w-fit font-medium"
												>{$i18n.t('User')}</span
											>
										{:else}
											<span class="bg-[#A99EC2] text-[#5D4497] font-medium dark:bg-[#33176E] rounded-[9px] py-[3px] text-xs text-white dark:text-[#7147CD] px-2 w-fit"
												>{$i18n.t('Admin')}</span
											>
										{/if}
									</div>
								</div>
							{/each}
						</div>
					</div>
				{/if}
			</div>
		</div>
		<div class="flex w-full items-start justify-between">
			<GroupSelect bind:selected={selectedGroups} {groups} placeholder="Add group..." />
			<button
				class="ml-2.5 whitespace-nowrap bg-lightGray-300 border-lightGray-400 text-lightGray-100 font-medium hover:bg-lightGray-550 text-xs dark:bg-customGray-900 border dark:border-customGray-700 dark:hover:bg-customGray-950 dark:text-customGray-200 py-2.5 px-4 h-12 rounded-lg transition"
				on:click={() => {
					inviteUsersHandler();
				}}
				type="button"
			>
				{$i18n.t('Send invites')}
			</button>
		</div>
	</form>
	<div class="flex justify-end mt-5 mb-1">
		<div
			class="flex w-[12rem] border dark:border-customGray-700 rounded-lg dark:bg-customGray-900 dark:text-customGray-200"
		>
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
		class="flex w-full justify-between items-center py-2.5 border-b border-lightGray-400 dark:border-customGray-700 mb-2.5"
	>
		<div class="flex w-full justify-start items-center">
			<div class="text-xs text-lightGray-100 dark:text-customGray-300 w-[calc(100%-250px)] font-medium">{$i18n.t('Users')}</div>
			<div class="text-xs text-lightGray-100 dark:text-customGray-300 font-medium">{$i18n.t('Roles')}</div>
		</div>
	</div>

	{#each filteredUsers as user, userIdx (user.id)}
		<div class="grid grid-cols-[244px_110px_100px_26px] gap-x-2 mb-2 group cursor-pointer">
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
				{#if user?.first_name !== 'INVITED'}
					<div class="text-xs dark:text-customGray-100 mr-1 whitespace-nowrap">
						{user.first_name}
						{user.last_name}
					</div>
				{/if}
				<Tooltip
					content={user.email}
					className=" w-fit overflow-hidden"
					placement="top-end"					>
					<div class="text-xs dark:text-customGray-590 mr-1 truncate text-ellipsis whitespace-nowrap">{user.email}</div>
			</Tooltip>
			</div>
			<div class="flex items-center">
				<div class="relative flex items-start w-fit">
					<button
						type="button"
						class="px-2 py-[3px] text-xs rounded-lg {user.role === 'user'
							? 'bg-[#99C3A3] dark:bg-[#024D15] text-[#1D7732] dark:text-[#0F8C18] font-medium'
							: 'bg-[#A99EC2] text-[#5D4497] font-medium dark:bg-[#33176E]  dark:text-[#7147CD]'}"
						on:click={() => (openDropdownIdx = openDropdownIdx === userIdx ? null : userIdx)}
					>
						{$i18n.t(user.role === 'user' ? 'User' : 'Admin')}
					</button>

					{#if openDropdownIdx === userIdx}
						<div
							use:onClickOutside={() => (openDropdownIdx = null)}
							class="absolute top-6 -right-4 z-10 py-1 bg-lightGray-300 dark:bg-customGray-900 rounded-md shadow-lg border dark:border-customGray-700"
						>
							<button
								class="flex justify-end w-full whitespace-nowrap text-left pl-2 pr-[6px] py-1 text-xs"
								on:click={() => {
									updateRoleHandler(user.id, 'user');
									openDropdownIdx = null;
								}}
							>
								<span class="bg-[#99C3A3] dark:bg-[#024D15] rounded-[9px] text-xs text-[#1D7732] dark:text-[#0F8C18] px-2 py-[3px] w-fit font-medium"
									>{$i18n.t('User')}</span
								>
							</button>
							<button
								class="flex justify-end w-full whitespace-nowrap text-left pl-2 pr-[6px] py-1 text-xs"
								on:click={() => {
									updateRoleHandler(user.id, 'admin');
									openDropdownIdx = null;
								}}
							>
								<span class="bg-[#A99EC2] text-[#5D4497] font-medium dark:bg-[#33176E] rounded-[9px] text-xs dark:text-[#7147CD] px-2 py-[3px] w-fit"
									>{$i18n.t('Admin')}</span
								>
							</button>
						</div>
					{/if}
				</div>
				<ChevronDown className="size-2 ml-[3px]" />
			</div>
			<div>
				{#if user?.first_name === 'INVITED'}
					<div
						class="self-center rounded-[9px] text-xs px-2 py-[3px] w-fit font-medium whitespace-nowrap bg-[#B4C1DB] dark:bg-[#113272] text-[#4169B8] dark:text-[#3F70CF]"
					>
						Invite pending
					</div>
				{/if}
			</div>
				<div class=" h-4">
					<InviteMenu {user} {getUsersHandler} {getSubscription}
					inviteCompleted={user?.first_name !== 'INVITED'}
					on:deleteUser={() => {
						showDeleteConfirm = true;
						userToDelete = user;
					}}
					>
						<button
							type="button"
							class="dark:text-white flex justify-between items-center rounded-md cursor-pointer invisible group-hover:visible"
						>
							<EllipsisHorizontal className="size-5" />
						</button>
					</InviteMenu>
				</div>
		</div>
	{/each}
</div>
