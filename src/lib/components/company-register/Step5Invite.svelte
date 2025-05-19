<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import { completeInvite } from '$lib/apis/auths';

	import {
		WEBUI_NAME,
		config,
		user,
		socket,
		toastVisible,
		toastMessage,
		toastType,
		showToast
	} from '$lib/stores';

	import Plus from '$lib/components/icons/Plus.svelte';
	import UserIcon from '$lib/components/icons/UserIcon.svelte';
	import ShowPassIcon from '$lib/components/icons/ShowPassIcon.svelte';
	import CustomToast from '$lib/components/common/CustomToast.svelte';
	import LoaderIcon from '$lib/components/icons/LoaderIcon.svelte';
	import { onClickOutside } from '$lib/utils';
	import ChevronDown from '../icons/ChevronDown.svelte';
	import { inviteUsers } from '$lib/apis/auths';
	import { error } from '@sveltejs/kit';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

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

	let emailFocused = false;

	const isValidEmail = (email: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());

	function addEmail() {
		const email = input.trim().toLowerCase();
		if (email && isValidEmail(email) && !invitedEmails.includes(email)) {
			invitedEmails = [...invitedEmails, email];
			input = '';
			dispatch('change', invitedEmails);
		}
	}

	function removeEmail(email: string) {
		invitedEmails = invitedEmails.filter((e) => e !== email);
		dispatch('change', invitedEmails);
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

	async function inviteHandler() {
		const invitees = invitedEmails.map(item => ({email: item, role: 'user'}));
		await inviteUsers(localStorage.token, invitees).catch(error => showToast('error', error));
		goto('/');			
	}

	let logoSrc = '/logo_light.png';

	onMount(() => {
		const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
		logoSrc = isDark ? '/logo_dark_transparent.png' : '/logo_light_transparent.png';
	});

</script>

<CustomToast message={$toastMessage} type={$toastType} visible={$toastVisible} />

<form
	class="flex flex-col self-center bg-lightGray-800 dark:bg-customGray-800 rounded-2xl w-[31rem] pt-8 px-24 pb-16"
	on:submit={(e) => {
		e.preventDefault();
		inviteHandler();
	}}
>
	<div class="self-center flex flex-col items-center mb-5">
		<div>
			<img crossorigin="anonymous" src={logoSrc} class=" w-10 mb-5" alt="logo" />
		</div>
		<div class="mb-2.5 font-medium text-lightGray-100 dark:text-customGray-100">{$i18n.t('Invite your team')}</div>
		<div class="text-center text-xs font-medium text-[#8A8B8D] dark:text-customGray-300">
			{$i18n.t('Invite your team to join your workspace')}
		</div>
	</div>
    <div class="bg-lightGray-300 dark:bg-customGray-900 rounded-md relative" style="min-height: 100px;">
		{#if invitedEmails?.length < 1 && !emailFocused}
				<div
					class="absolute left-2.5 text-sm top-2.5 text-lightGray-100 bg-lightGray-300 dark:text-customGray-100 dark:bg-customGray-900 pointer-events-none w-[100px] h-6"
				>
					{$i18n.t('Emails')}
				</div>
				<span
					class="absolute top-[26px] w-[12rem] text-lightGray-100/50 text-right right-2.5 -translate-y-1/2 text-xs dark:text-customGray-100/50 pointer-events-none select-none"
				>
					{$i18n.t('Add Team member mails (separated by comma)')}
				</span>
			{/if}
        <div
            
            class="flex flex-wrap gap-1 items-start p-3 "
            on:click={() => inputRef.focus()}
        >
            {#each invitedEmails as email, index (email)}
                <div
                    style={`background-color: ${emailColors[index%emailColors.length]}`}
                    class="flex items-start  text-xs px-2 py-1 rounded-full text-white dark:text-white"
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
                class="text-xs bg-transparent outline-none px-1 h-6 min-w-[80px] text-lightGray-100 dark:text-customGray-100"
                on:keydown={handleKeydown}
                on:blur={() => {
					addEmail()
					emailFocused = false
					}}
				on:focus={() => (emailFocused = true)}
				on:input={updateInputWidth}
            />
			<span bind:this={ghostRef} class="invisible absolute whitespace-pre text-xs px-1"></span>
        </div>
    </div>
    <div class="mt-2.5 flex justify-end gap-7">
        <button
            class="font-medium w-fit text-xs text-lightGray-100 dark:text-customGray-200 py-2.5 rounded-lg transition"
            on:click={() => {
              goto('/');
            }}
            type="button"
        >
            {$i18n.t('Skip for now')}
        </button>
        <button
            class="font-medium bg-lightGray-300 hover:bg-lightGray-700 text-lightGray-100 text-xs dark:bg-customGray-900 border dark:border-customGray-700 dark:hover:bg-customGray-950 dark:text-customGray-200 w-1/2 py-2.5 rounded-lg transition"
        >
            {$i18n.t('Invite')}
        </button>
    </div>
</form>
