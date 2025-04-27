<script lang="ts">
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
	import { createEventDispatcher } from 'svelte';
    import { onClickOutside } from '$lib/utils';
    import ChevronDown from '../icons/ChevronDown.svelte';

	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	let companyName = '';
    
	let loading = false;

	const confirmHandler = async () => {
		
		dispatch('next');
	};

	let logoSrc = '/logo_light.png';

	onMount(() => {
		const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
		logoSrc = isDark ? '/logo_dark_transparent.png' : '/logo_dark.png';
	});

	$: console.log($WEBUI_NAME);

    let companySizeDropdown = false;
    let companySizeDropdownRef;
    let companySizeOptions = [{id: '1', label: '1-10'}, {id: '2', label: '11-20'}, {id: '3', label: '21-30'}]
    
    let companySize = companySizeOptions[0];

    let industryDropdown = false;
    let industryDropdownRef;
    let industryOptions = [{ id: '1', label: 'Technology' },
	{ id: '2', label: 'Healthcare' },
	{ id: '3', label: 'Finance' },
	{ id: '4', label: 'Education' },
	{ id: '5', label: 'Retail' },
	{ id: '6', label: 'Manufacturing' },
	{ id: '7', label: 'Real Estate' },
	{ id: '8', label: 'Transportation' },
	{ id: '9', label: 'Marketing & Advertising' },
	{ id: '10', label: 'Legal' }]

    let industry = industryOptions[0];

    let teamDropdown = false;
    let teamDropdownRef;
    let teamOptions = [
        { id: '1', label: 'Sales' },
        { id: '2', label: 'Marketing' },
        { id: '3', label: 'Customer Support' },
        { id: '4', label: 'Product Management' },
        { id: '5', label: 'Engineering' },
        { id: '6', label: 'Design' },
        { id: '7', label: 'Human Resources' },
        { id: '8', label: 'Operations' },
        { id: '9', label: 'Finance' },
        { id: '10', label: 'Legal' }
    ];
    let team = teamOptions[0];

</script>

<svelte:head>
	<title>
		{`${$WEBUI_NAME}`}
	</title>
</svelte:head>

<CustomToast message={$toastMessage} type={$toastType} visible={$toastVisible} />

<form
	class="flex flex-col self-center dark:bg-customGray-800 rounded-2xl w-[31rem] pt-8 px-24 pb-16"
	on:submit={(e) => {
		e.preventDefault();
		confirmHandler();
	}}
>
	<div class="self-center flex flex-col items-center mb-5">
		<div>
			<img crossorigin="anonymous" src="/logo_dark_transparent.png" class=" w-10 mb-5" alt="logo" />
		</div>
		<div class="mb-2.5">{$i18n.t('Company and Team Information')}</div>
		<div class="text-center text-xs dark:text-customGray-300">
			{$i18n.t('Let’s go to know your company ant team')}
		</div>
	</div>

	<div class="flex-1 mb-2.5">
		<div class="relative w-full dark:bg-customGray-900 rounded-md">
			{#if companyName}
				<div class="text-xs absolute left-2.5 top-1 dark:text-customGray-100/50">
					{$i18n.t('Name')}
				</div>
			{/if}
			<input
				class={`px-2.5 text-sm ${companyName ? 'mt-2' : 'mt-0'} w-full h-10 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none`}
				placeholder={$i18n.t('Name')}
				bind:value={companyName}
				required
			/>
		</div>
	</div>
    <div class="mb-2.5" use:onClickOutside={() => (companySizeDropdown = false)}>
        <div class="relative" bind:this={companySizeDropdownRef}>
            <button
                type="button"
                class={`flex items-center justify-between w-full text-sm h-10 px-3 py-2 ${
                    companySizeDropdown ? 'border' : ''
                } border-gray-300 dark:border-customGray-700 rounded-md bg-white dark:bg-customGray-900 cursor-pointer`}
                on:click={() => {
                    companySizeDropdown = !companySizeDropdown
                    }}
            >
                <span class="text-gray-500 dark:text-customGray-100"
                    >{$i18n.t('Company Size')}</span
                >
               
                <div class="flex items-center gap-2 text-xs dark:text-customGray-100/50">
                    { companySize?.label}
                    <ChevronDown className="size-3" />
                </div>
               
            </button>

            {#if companySizeDropdown}
                <div
                    class="max-h-40 overflow-y-auto absolute z-50 w-full -mt-1 bg-white pb-1 dark:bg-customGray-900 border-l border-r border-b border-gray-300 dark:border-customGray-700 rounded-b-md shadow"
                >
                    <hr class="border-t border-customGray-700 mb-2 mt-1 mx-0.5" />
                    <div class="px-1">
                        {#each companySizeOptions as option}
                            <button
                                class="px-3 py-2 flex items-center gap-2 w-full rounded-xl text-sm hover:bg-gray-100 dark:hover:bg-customGray-950 dark:text-customGray-100 cursor-pointer text-gray-900"
                                on:click={() => {
                                    companySize = option;
                                    companySizeDropdown = false;
                                }}
                            >
                                {option.label}
                            </button>
                        {/each}
                    </div>
                </div>
            {/if}
        </div>
    </div>
    <div class="mb-2.5" use:onClickOutside={() => (industryDropdown = false)}>
        <div class="relative" bind:this={industryDropdownRef}>
            <button
                type="button"
                class={`flex items-center justify-between w-full text-sm h-10 px-3 py-2 ${
                    industryDropdown ? 'border' : ''
                } border-gray-300 dark:border-customGray-700 rounded-md bg-white dark:bg-customGray-900 cursor-pointer`}
                on:click={() => {
                    industryDropdown = !industryDropdown
                    }}
            >
                <span class="text-gray-500 dark:text-customGray-100"
                    >{$i18n.t('Industry')}</span
                >
               
                <div class="flex items-center gap-2 text-xs dark:text-customGray-100/50">
                    { industry?.label}
                    <ChevronDown className="size-3" />
                </div>
               
            </button>

            {#if industryDropdown}
                <div
                    class="max-h-40 overflow-y-auto absolute z-50 w-full -mt-1 bg-white pb-1 dark:bg-customGray-900 border-l border-r border-b border-gray-300 dark:border-customGray-700 rounded-b-md shadow"
                >
                    <hr class="border-t border-customGray-700 mb-2 mt-1 mx-0.5" />
                    <div class="px-1">
                        {#each industryOptions as option}
                            <button
                                class="px-3 py-2 flex items-center gap-2 w-full rounded-xl text-sm hover:bg-gray-100 dark:hover:bg-customGray-950 dark:text-customGray-100 cursor-pointer text-gray-900"
                                on:click={() => {
                                    industry = option;
                                    industryDropdown = false;
                                }}
                            >
                                {option.label}
                            </button>
                        {/each}
                    </div>
                </div>
            {/if}
        </div>
    </div>

    <div class="mb-2.5" use:onClickOutside={() => (teamDropdown = false)}>
        <div class="relative" bind:this={teamDropdownRef}>
            <button
                type="button"
                class={`flex items-center justify-between w-full text-sm h-10 px-3 py-2 ${
                    teamDropdown ? 'border' : ''
                } border-gray-300 dark:border-customGray-700 rounded-md bg-white dark:bg-customGray-900 cursor-pointer`}
                on:click={() => {
                    teamDropdown = !teamDropdown
                    }}
            >
                <span class="text-gray-500 dark:text-customGray-100"
                    >{$i18n.t('Team Function')}</span
                >
               
                <div class="flex items-center gap-2 text-xs dark:text-customGray-100/50">
                    {team?.label}
                    <ChevronDown className="size-3" />
                </div>
               
            </button>

            {#if teamDropdown}
                <div
                    class="max-h-40 overflow-y-auto absolute z-50 w-full -mt-1 bg-white pb-1 dark:bg-customGray-900 border-l border-r border-b border-gray-300 dark:border-customGray-700 rounded-b-md shadow"
                >
                    <hr class="border-t border-customGray-700 mb-2 mt-1 mx-0.5" />
                    <div class="px-1">
                        {#each teamOptions as option}
                            <button
                                class="px-3 py-2 flex items-center gap-2 w-full rounded-xl text-sm hover:bg-gray-100 dark:hover:bg-customGray-950 dark:text-customGray-100 cursor-pointer text-gray-900"
                                on:click={() => {
                                    team = option;
                                    teamDropdown = false;
                                }}
                            >
                                {option.label}
                            </button>
                        {/each}
                    </div>
                </div>
            {/if}
        </div>
    </div>

	
	<button
		class=" text-xs w-full h-10 px-3 py-2 transition rounded-lg {loading
			? ' cursor-not-allowed bg-black hover:bg-gray-900 text-white dark:bg-customGray-950 dark:hover:bg-customGray-950 dark:text-white border dark:border-customGray-700'
			: 'bg-black hover:bg-gray-900 text-white dark:bg-customGray-900 dark:hover:bg-customGray-950 dark:text-customGray-200 border dark:border-customGray-700'} flex justify-center items-center"
		type="submit"
		disabled={loading}
	>
		{$i18n.t('Continue')}
		{#if loading}
			<div class="ml-1.5 self-center">
				<LoaderIcon />
			</div>
		{/if}
	</button>
</form>
