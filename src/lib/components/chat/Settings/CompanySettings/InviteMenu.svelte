<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { createEventDispatcher, getContext } from 'svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import MessageEditIcon from '$lib/components/icons/MessageEditIcon.svelte';
	import DeleteIcon from '$lib/components/icons/DeleteIcon.svelte';
	import ShareIcon from '$lib/components/icons/ShareIcon.svelte';
	import PermissionIcon from '$lib/components/icons/PermissionIcon.svelte';
	import RevokeInvite from '$lib/components/icons/RevokeInvite.svelte';
	import { onClickOutside } from '$lib/utils';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import { reinviteUser, revokeInvite } from '$lib/apis/users';
	import { toast } from 'svelte-sonner';
	import WebSearchIcon from '$lib/components/icons/WebSearchIcon.svelte';
	import ImageGenerateIcon from '$lib/components/icons/ImageGenerateIcon.svelte';
	import CodeInterpreterIcon from '$lib/components/icons/CodeInterpreterIcon.svelte';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import { copyToClipboard } from '$lib/utils';
	

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();
	export let user = null;

	export let getUsersHandler: Function;
	export let getSubscription: Function;

	export let inviteCompleted = false;
	let showDropdown = false;

	let root;

	async function reinvite() {
		await reinviteUser(localStorage.token, user?.email)
		.then(() => toast.success($i18n.t('Successfully resend invite')))
		.catch((error) => {
			toast.error(`${error}`);
		});		
	}

	async function revokeInviteHandler() {
		const res = await revokeInvite(localStorage.token, user?.email).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		getUsersHandler();
		getSubscription();
		toast.success($i18n.t('Invite revoked successfuly'));
	}
	async function copyInviteLink(token) {
		const origin = window.location.origin;
		const link = `${origin}/register?inviteToken=${token}`
		await copyToClipboard(link);
		toast.success($i18n.t('Copied'));
	}

	$: console.log(showDropdown, 'show dropdown')
</script>

<div>
	<div bind:this={root} class="relative w-full" use:onClickOutside={() => (showDropdown = false)}>
		<div
		on:click={() => (showDropdown = !showDropdown)}
	>
		<slot/>
	</div>
		{#if showDropdown}
			<div
				class="w-[10rem] flex flex-col absolute left-0 right-0 bg-white dark:bg-customGray-900 px-1 py-2 border border-gray-300 dark:border-customGray-700 rounded-lg z-10"
			>
				{#if (inviteCompleted)}
					<button
						type="button"
						on:click={() => {
							dispatch('deleteUser')
						}}
						class="flex gap-2 items-center px-3 py-2 text-xs text-[#F65351] font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-customGray-950 rounded-md"
					>
						<DeleteIcon />
						<div class="flex items-center">{$i18n.t('Delete user')}</div>
					</button>
				{:else}
					<button
						type="button"
						on:click={reinvite}
						class="flex gap-2 items-center px-3 py-2 text-xs dark:text-customGray-100 font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-customGray-950 rounded-md dark:hover:text-white"
					>
						<MessageEditIcon />
						<div class="flex items-center">{$i18n.t('Resend invite')}</div>
					</button>

					<button
						type="button"
						on:click={() => {
							copyInviteLink(user.invite_token)
						}}
						class="flex gap-2 items-center px-3 py-2 text-xs dark:text-customGray-100 font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-customGray-950 rounded-md dark:hover:text-white"
					>
						<ShareIcon />
						<div class="flex items-center">{$i18n.t('Copy invite link')}</div>
					</button>
					<button
						type="button"
						on:click={revokeInviteHandler}
						class="flex gap-2 items-center px-3 py-2 text-xs dark:text-customGray-100 font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-customGray-950 rounded-md dark:hover:text-white"
					>
						<RevokeInvite />
						<div class="flex items-center">{$i18n.t('Revoke invite')}</div>
					</button>
				{/if}	
			</div>
		{/if}
	</div>
</div>
