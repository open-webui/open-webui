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
    import HidePassIcon from '../icons/HidePassIcon.svelte';
    import InfoIcon from '../icons/InfoIcon.svelte';
    import Tooltip from '../common/Tooltip.svelte';

	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	
	export let first_name = '';
	export let last_name = '';
    export let profile_image_url = '';
	export let password = '';
	let showPassword = false;
	let confirmPassword = '';
	let showConfirmPassword = false;

    let profileImageInputElement;

	let loading = false;

	const confirmHandler = async () => {
		if (password !== confirmPassword) {
			showToast(
				'error',
				`The passwords you entered don't quite match. Please double-check and try again.`
			);
			return;
		}
		const strongPasswordRegex =
			/^(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]).{8,}$/;

		if (!strongPasswordRegex.test(password)) {
			showToast(
				'error',
				'Password must be 8+ characters, with a number, capital letter, and symbol.'
			);
			return;
		}
		dispatch('next');
	};

	let logoSrc = '/logo_light.png';

	onMount(() => {
		const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
		logoSrc = isDark ? '/logo_dark_transparent.png' : '/logo_light_transparent.png';
	});

	$: console.log($WEBUI_NAME);
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
        <div class="text-lightGray-100 dark:text-customGray-100 font-medium">{$i18n.t('Add personal information')}</div>
    </div>
    <input
			id="profile-image-input"
			bind:this={profileImageInputElement}
			type="file"
			hidden
			accept="image/*"
			on:change={(e) => {
				const files = profileImageInputElement.files ?? [];
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
						profile_image_url = compressedSrc;

						profileImageInputElement.files = null;
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
                    profileImageInputElement.click();
                }}
            >
                {#if profile_image_url}
                    <img
                        src={profile_image_url}
                        alt="model profile"
                        class="rounded-lg size-16 object-cover shrink-0"
                    />
                {:else}
                    <div class="rounded-lg size-16 shrink-0 bg-lightGray-400  dark:bg-customGray-900 dark:text-customGray-800">
                        <UserIcon className="size-16"/>
                    </div>
                {/if}

                <div class="absolute bottom-0 right-0 z-10">
                    <div class="-m-2">
                        <div
                            class="p-1 rounded-lg border bg-lightGray-300 dark:bg-customGray-900 text-lightGray-1200 transition border-lightGray-1200 dark:border-customGray-700 dark:text-white"
                        >
                            <Plus className="size-3" />
                        </div>
                    </div>
                    <div class="text-xs -top-1 left-5 dark:text-customGray-200 absolute whitespace-nowrap">{$i18n.t('Add a photo')}</div>  
                </div>
            </button>
        </div>
    </div>
    <div class="text-xs font-medium text-[#8A8B8D] dark:text-customGray-100/50 mb-2.5 mt-5">{$i18n.t('We only support PNGs, JPEGs and GIFs under 10MB')}</div>
	
	<div class="flex-1 mb-2.5">
		<div class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md">
			{#if first_name}
				<div class="text-xs absolute left-2.5 top-1 text-lightGray-100/50 dark:text-customGray-100/50">
					{$i18n.t('First Name')}
				</div>
			{/if}
			<input
				class={`px-2.5 text-sm ${first_name ? 'pt-2' : 'pt-0'} text-lightGray-100 placeholder:text-lightGray-100 w-full h-12 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none`}
				placeholder={$i18n.t('First Name')}
				bind:value={first_name}
				required
			/>
		</div>
	</div>

	<div class="flex-1 mb-2.5">
		<div class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md">
			{#if last_name}
				<div class="text-xs absolute left-2.5 top-1 text-lightGray-100/50 dark:text-customGray-100/50">
					{$i18n.t('Last Name')}
				</div>
			{/if}
			<input
				class={`px-2.5 text-sm ${last_name ? 'pt-2' : 'pt-0'} text-lightGray-100 placeholder:text-lightGray-100 w-full h-12 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none`}
				placeholder={$i18n.t('Last Name')}
				bind:value={last_name}
				required
			/>
		</div>
	</div>

	<div class="relative flex flex-col w-full mb-2.5">
		<div class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md">
			{#if password}
				<div class="text-xs absolute left-2.5 top-1 text-lightGray-100/50 dark:text-customGray-100/50">
					{$i18n.t('Create Password')}
				</div>
			{/if}
			{#if showPassword}
				<input
					class={`px-2.5 text-sm ${password ? 'pt-2' : 'pt-0'} text-lightGray-100 placeholder:text-lightGray-100 w-full h-12 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none pr-10`}
					type="text"
					bind:value={password}
					placeholder={$i18n.t('Create Password')}
					autocomplete="new-password"
					required
				/>
			{:else}
				<input
					class={`px-2.5 text-sm ${password ? 'pt-2' : 'pt-0'} text-lightGray-100 placeholder:text-lightGray-100 w-full h-12 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none pr-10`}
					type="password"
					bind:value={password}
					placeholder={$i18n.t('Create Password')}
					autocomplete="new-password"
					required
				/>
			{/if}

			<button
				type="button"
				class="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-gray-500 dark:text-white"
				on:click={() => (showPassword = !showPassword)}
				tabindex="-1"
			>
            {#if showPassword}
                <HidePassIcon/>
            {:else}
                <ShowPassIcon/>
            {/if}
			</button>
		</div>
        <Tooltip className="absolute -right-6 top-3 cursor-pointer" content={$i18n.t('Password must be 8+ characters, with a number, capital letter, and symbol.')}>
            <div class="flex justify-center items-center w-[18px] h-[18px] rounded-full dark:bg-customGray-700">
                <InfoIcon className="size-6"/>
            </div>
        </Tooltip>       
	</div>
	<div class="flex flex-col w-full mb-2.5">
		<div class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md">
			{#if confirmPassword}
				<div class="text-xs absolute left-2.5 top-1 text-lightGray-100/50 dark:text-customGray-100/50">
					{$i18n.t('Confirm password')}
				</div>
			{/if}
			{#if showConfirmPassword}
				<input
					class={`px-2.5 text-sm ${confirmPassword ? 'pt-2' : 'pt-0'} text-lightGray-100 placeholder:text-lightGray-100 w-full h-12 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none pr-10`}
					type="text"
					bind:value={confirmPassword}
					placeholder={$i18n.t('Confirm Password')}
					autocomplete="new-password"
					required
				/>
			{:else}
				<input
					class={`px-2.5 text-sm ${confirmPassword ? 'pt-2' : 'pt-0'} text-lightGray-100 placeholder:text-lightGray-100 w-full h-12 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none pr-10`}
					type="password"
					bind:value={confirmPassword}
					placeholder={$i18n.t('Confirm Password')}
					autocomplete="new-password"
					required
				/>
			{/if}

			<button
				type="button"
				class="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-gray-500 dark:text-white"
				on:click={() => (showConfirmPassword = !showConfirmPassword)}
				tabindex="-1"
			>
            {#if showConfirmPassword}
                <HidePassIcon/>
            {:else}
                <ShowPassIcon/>
            {/if}
			</button>
		</div>
	</div>
	<button
		class=" text-xs w-full h-10 px-3 py-2 font-medium transition rounded-lg {loading
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
