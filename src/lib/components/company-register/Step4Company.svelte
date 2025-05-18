<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

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
    import { COMPANY_SIZE_OPTIONS, INDUSTRY_OPTIONS, TEAM_FUNCTION_OPTIONS } from '$lib/constants';
    import CompanyIcon from '../icons/CompanyIcon.svelte';

	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

   
	export let company_name = '';
    export let company_profile_image_url = '';
    export let company_size = '';
    export let company_industry = '';
	export let company_team_function = '';
    
	let loading = false;

	const confirmHandler = async () => {
		
		dispatch('next');
	};

	let logoSrc = '/logo_light.png';

	onMount(() => {
		const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
		logoSrc = isDark ? '/logo_dark_transparent.png' : '/logo_light_transparent.png';
	});

	$: console.log($WEBUI_NAME);

    let companySizeDropdown = false;
    let companySizeDropdownRef;
 
    

    let industryDropdown = false;
    let industryDropdownRef;
    

    let teamDropdown = false;
    let teamDropdownRef;

    let logoImageInputElement;
    
</script>

<svelte:head>
	<title>
		{`${$WEBUI_NAME}`}
	</title>
</svelte:head>

<CustomToast message={$toastMessage} type={$toastType} visible={$toastVisible} />

<form
	class="flex flex-col self-center bg-lightGray-800 dark:bg-customGray-800 rounded-2xl w-[31rem] pt-8 px-24 pb-16"
	on:submit={(e) => {
		e.preventDefault();
		confirmHandler();
	}}
>
	<div class="self-center flex flex-col items-center mb-5">
		<div>
			<img crossorigin="anonymous" src={logoSrc} class=" w-10 mb-5" alt="logo" />
		</div>
		<div class="mb-2.5 font-medium text-lightGray-100 dark:text-customGray-100">{$i18n.t('Company & Team Information')}</div>
		<div class="text-center text-xs font-medium text-[#8A8B8D] dark:text-customGray-300">
			{$i18n.t('Let’s get to know your company and team.')}
		</div>
	</div>
    <input
			id="profile-image-input"
			bind:this={logoImageInputElement}
			type="file"
			hidden
			accept="image/*"
			on:change={(e) => {
				const files = logoImageInputElement.files ?? [];
				let reader = new FileReader();
				reader.onload = (event) => {
					let originalImageUrl = `${event.target.result}`;

					const img = new Image();
					img.src = originalImageUrl;

					img.onload = function () {
						const canvas = document.createElement('canvas');
						const ctx = canvas.getContext('2d');

						// Calculate the aspect ratio of the image
						const aspectRatio = img.width / img.height;

						// Calculate the new width and height to fit within 250x250
						let newWidth, newHeight;
						if (aspectRatio > 1) {
							newWidth = 250 * aspectRatio;
							newHeight = 250;
						} else {
							newWidth = 250;
							newHeight = 250 / aspectRatio;
						}

						// Set the canvas size
						canvas.width = 250;
						canvas.height = 250;

						// Calculate the position to center the image
						const offsetX = (250 - newWidth) / 2;
						const offsetY = (250 - newHeight) / 2;

						// Draw the image on the canvas
						ctx.drawImage(img, offsetX, offsetY, newWidth, newHeight);

						// Get the base64 representation of the compressed image
						const compressedSrc = canvas.toDataURL('image/jpeg');

						// Display the compressed image
						company_profile_image_url = compressedSrc;

						logoImageInputElement.files = null;
					};
				};

				if (
					files.length > 0 &&
					['image/gif', 'image/webp', 'image/jpeg', 'image/png'].includes(files[0]['type'])
				) {
					reader.readAsDataURL(files[0]);
				}
			}}
		/>
    <div class="self-center flex justify-center flex-shrink-0">
        <div class="self-center">
            <button
                class="rounded-xl flex flex-shrink-0 items-center shadow-xl group relative"
                type="button"
                on:click={() => {
                    logoImageInputElement.click();
                }}
            >
                {#if company_profile_image_url}
                    <img
                        src={company_profile_image_url}
                        alt="model profile"
                        class="rounded-lg size-16 object-cover shrink-0"
                    />
                {:else}
                    <div class="rounded-lg flex justify-center size-16 shrink-0 bg-lightGray-400 dark:bg-customGray-900 text-white dark:text-customGray-800">
                        <CompanyIcon className="self-center size-12"/>
                    </div>
                {/if}

                <div class="absolute bottom-0 right-0 z-10">
                    <div class="-m-2">
                        <div
                            class="p-1 rounded-lg border border-lightGray-1200 dark:bg-customGray-900 bg-lightGray-300 text-lightGray-1200 transition dark:border-customGray-700 dark:text-white"
                        >
                            <Plus className="size-3" />
                        </div>
                    </div>
                    <div class="text-xs -top-1 left-5 dark:text-customGray-200 absolute whitespace-nowrap">{$i18n.t('Add company logo')}</div>  
                </div>
            </button>
        </div>
    </div>
    <div class="text-xs dark:text-customGray-100/50 mb-2.5 mt-5">{$i18n.t('We only support PNGs, JPEGs and GIFs under 10MB')}</div>

	<div class="flex-1 mb-2.5">
		<div class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md">
			{#if company_name}
				<div class="text-xs absolute text-lightGray-100/50 left-2.5 top-1 dark:text-customGray-100/50">
					{$i18n.t('Name')}
				</div>
			{/if}
			<input
				class={`px-2.5 text-sm ${company_name ? 'pt-2' : 'pt-0'} text-lightGray-100 placeholder:text-lightGray-100 w-full h-12 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none`}
				placeholder={$i18n.t('Name')}
				bind:value={company_name}
				required
			/>
		</div>
	</div>
    <div class="mb-2.5" use:onClickOutside={() => (companySizeDropdown = false)}>
        <div class="relative" bind:this={companySizeDropdownRef}>
            <button
                type="button"
                class={`flex items-center justify-between w-full text-sm h-12 px-3 py-2 ${
                    companySizeDropdown ? 'border' : ''
                } border-lightGray-400 dark:border-customGray-700 rounded-md bg-lightGray-300 dark:bg-customGray-900 cursor-pointer`}
                on:click={() => {
                    companySizeDropdown = !companySizeDropdown
                    }}
            >
                <span class="text-lightGray-100 dark:text-customGray-100"
                    >{$i18n.t('Company Size')}</span
                >
               
                <div class="flex items-center gap-2 text-xs text-lightGray-100 dark:text-customGray-100/50">
                    { company_size}
                    <ChevronDown className="size-3" />
                </div>
               
            </button>

            {#if companySizeDropdown}
                <div
                    class="custom-scrollbar max-h-40 overflow-y-auto absolute z-50 w-full -mt-1 bg-lightGray-300 pb-1 dark:bg-customGray-900 border-l border-r border-b boder-lightGray-400 dark:border-customGray-700 rounded-b-md"
                >
                    <hr class="border-t border-lightGray-400 dark:border-customGray-700 mb-2 mt-1 mx-0.5" />
                    <div class="px-1">
                        {#each COMPANY_SIZE_OPTIONS as option}
                            <button
                                class="px-3 py-2 flex items-center gap-2 w-full rounded-xl text-sm hover:bg-lightGray-700 dark:hover:bg-customGray-950 dark:text-customGray-100 cursor-pointer text-gray-900"
                                on:click={() => {
                                    company_size = option;
                                    companySizeDropdown = false;
                                }}
                            >
                                {option}
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
                class={`flex items-center justify-between w-full text-sm h-12 px-3 py-2 ${
                    industryDropdown ? 'border' : ''
                } border-lightGray-400 dark:border-customGray-700 rounded-md bg-lightGray-300 dark:bg-customGray-900 cursor-pointer`}
                on:click={() => {
                    industryDropdown = !industryDropdown
                    }}
            >
                <span class="text-lightGray-100 dark:text-customGray-100"
                    >{$i18n.t('Industry')}</span
                >
               
                <div class="flex items-center gap-2 text-xs text-lightGray-100 dark:text-customGray-100/50">
                    { company_industry}
                    <ChevronDown className="size-3" />
                </div>
               
            </button>

            {#if industryDropdown}
                <div
                    class="custom-scrollbar max-h-40 overflow-y-auto absolute z-50 w-full -mt-1 bg-lightGray-300 pb-1 dark:bg-customGray-900 border-l border-r border-b boder-lightGray-400 dark:border-customGray-700 rounded-b-md"
                >
                    <hr class="border-t border-lightGray-400 dark:border-customGray-700 mb-2 mt-1 mx-0.5" />
                    <div class="px-1">
                        {#each INDUSTRY_OPTIONS as option}
                            <button
                                class="px-3 py-2 flex items-center gap-2 w-full rounded-xl text-sm hover:bg-lightGray-700 dark:hover:bg-customGray-950 dark:text-customGray-100 cursor-pointer text-gray-900"
                                on:click={() => {
                                    company_industry = option;
                                    industryDropdown = false;
                                }}
                            >
                                {option}
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
                class={`flex items-center justify-between w-full text-sm h-12 px-3 py-2 ${
                    teamDropdown ? 'border' : ''
                } border-lightGray-400 dark:border-customGray-700 rounded-md bg-lightGray-300 dark:bg-customGray-900 cursor-pointer`}
                on:click={() => {
                    teamDropdown = !teamDropdown
                    }}
            >
                <span class="text-lightGray-100 dark:text-customGray-100"
                    >{$i18n.t('Team Function')}</span
                >
               
                <div class="flex items-center gap-2 text-xs text-lightGray-100 dark:text-customGray-100/50">
                    {company_team_function}
                    <ChevronDown className="size-3" />
                </div>
               
            </button>

            {#if teamDropdown}
                <div
                    class="custom-scrollbar max-h-40 overflow-y-auto absolute z-50 w-full -mt-1 bg-lightGray-300 pb-1 dark:bg-customGray-900 border-l border-r border-b boder-lightGray-400 dark:border-customGray-700 rounded-b-md"
                >
                    <hr class="border-t border-lightGray-400 dark:border-customGray-700 mb-2 mt-1 mx-0.5" />
                    <div class="px-1">
                        {#each TEAM_FUNCTION_OPTIONS as option}
                            <button
                                class="px-3 py-2 flex items-center gap-2 w-full rounded-xl text-sm hover:bg-lightGray-700 dark:hover:bg-customGray-950 dark:text-customGray-100 cursor-pointer text-gray-900"
                                on:click={() => {
                                    company_team_function = option;
                                    teamDropdown = false;
                                }}
                            >
                                {option}
                            </button>
                        {/each}
                    </div>
                </div>
            {/if}
        </div>
    </div>

	
	<button
		class=" text-xs w-full h-10 px-3 py-2 transition font-medium rounded-lg {loading
			? ' cursor-not-allowed bg-lightGray-300 hover:bg-lightGray-550 text-lightGray-100 dark:bg-customGray-950 dark:hover:bg-customGray-950 dark:text-white border border-lightGray-400 dark:border-customGray-700'
			: 'bg-lightGray-300 hover:bg-lightGray-550 text-lightGray-100 dark:bg-customGray-900 dark:hover:bg-customGray-950 dark:text-customGray-200 border border-lightGray-400 dark:border-customGray-700'} flex justify-center items-center"
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
