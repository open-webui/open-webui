<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import { completeInvite, getCompanyDetails, getCompanyConfig } from '$lib/apis/auths';

	import { WEBUI_NAME, config, user, socket, toastVisible, toastMessage, toastType, showToast, company, companyConfig } from '$lib/stores';

	import Plus from '$lib/components/icons/Plus.svelte';
	import UserIcon from '$lib/components/icons/UserIcon.svelte';
	import ShowPassIcon from '$lib/components/icons/ShowPassIcon.svelte';
	import CustomToast from '$lib/components/common/CustomToast.svelte';
	import LoaderIcon from '$lib/components/icons/LoaderIcon.svelte';
	import HidePassIcon from '$lib/components/icons/HidePassIcon.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import InfoIcon from '$lib/components/icons/InfoIcon.svelte';
	import { generateInitialsImage } from '$lib/utils';

	const i18n = getContext('i18n');

	let firstName = '';
	let lastName = '';
	let password = '';
	let showPassword = false;
	let confirmPassword = '';
	let showConfirmPassword = '';

	let inviteToken = '';

	let profileImageUrl = '';

	let profileImageInputElement;

	let loading = false;

	onMount(() => {
		if ($page.url.searchParams.get('inviteToken')) {
			inviteToken = $page.url.searchParams.get('inviteToken')
		}else{
			goto('/company-register')
		}
	})

	const setSessionUser = async (sessionUser) => {
		if (sessionUser) {
			console.log(sessionUser);
			showToast('success', `You're now logged in.`);
			if (sessionUser.token) {
				localStorage.token = sessionUser.token;
			}

			$socket.emit('user-join', { auth: { token: sessionUser.token } });
			await user.set(sessionUser);
			await config.set(await getBackendConfig());
			goto('/');
		}
	};

	const completeInviteHandler = async () => {
		if (password !== confirmPassword) {
			showToast('error', `The passwords you entered don't quite match. Please double-check and try again.`);
			return;
		}
		const strongPasswordRegex = /^(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]).{8,}$/;

		if (!strongPasswordRegex.test(password)) {
			showToast('error', "Password must be 8+ characters, with a number, capital letter, and symbol.");
			return;
		}
		loading = true;
		const sessionUser = await completeInvite(firstName, lastName, password, inviteToken, profileImageUrl ? profileImageUrl : generateInitialsImage(`${firstName} ${lastName}`)).catch(
			(error) => {
				toast.error(`${error}`);
				loading = false;
				return null;
			}
		);
		await setSessionUser(sessionUser);
		
		const [companyInfo, companyConfigInfo] = await Promise.all([
			getCompanyDetails(sessionUser.token).catch((error) => {
				toast.error(`${error}`);
				return null;
			}),
			getCompanyConfig(sessionUser.token).catch((error) => {
				toast.error(`${error}`);
				return null;
			})
		]);

		if (companyInfo) {
			company.set(companyInfo);
		}

		if (companyConfigInfo) {
			console.log(companyConfigInfo);
			companyConfig.set(companyConfigInfo);
		}
		loading = false;
	}

	onMount(async () => {});
	let logoSrc = '/logo_light.png';

	onMount(() => {
		const isDark = localStorage.getItem('theme') === 'dark';
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
<div
	class="flex flex-col justify-between w-full h-screen max-h-[100dvh] px-4 text-lightGray-100 dark:text-white relative bg-lightGray-300 dark:bg-customGray-900"
>
	<div class="font-medium self-center flex flex-col items-center mt-5">
		<div>
			<img crossorigin="anonymous" src={logoSrc} class=" w-10 mb-5" alt="logo" />
		</div>
		<div>{$i18n.t('Welcome to')} Beyond Chat</div>
	</div>
	<form
		class="flex flex-col self-center bg-lightGray-800 dark:bg-customGray-800 rounded-2xl w-full md:w-[31rem] px-5 py-5 md:pt-8 md:px-24 md:pb-16"
		on:submit={(e) => {
			e.preventDefault();
			completeInviteHandler();
		}}
	>
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
						profileImageUrl = compressedSrc;

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
					{#if profileImageUrl}
						<img
							src={profileImageUrl}
							alt="model profile"
							class="rounded-lg size-16 object-cover shrink-0"
						/>
					{:else}
						<div class="rounded-lg size-16 shrink-0 bg-lightGray-400 text-white dark:bg-customGray-900 dark:text-customGray-800">
							<UserIcon className="size-16"/>
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
						<div class="text-xs -top-1 left-5 text-[#8A8B8D] font-medium dark:text-customGray-200 absolute whitespace-nowrap">{$i18n.t('Add a photo')}</div>
					</div>
				</button>
			</div>
		</div>
		<div class="text-xs text-[#8A8B8D] font-medium dark:text-customGray-100/50 mb-2.5 mt-5">{$i18n.t('We only support PNGs, JPEGs and GIFs under 10MB')}</div>
		<div class="flex-1 mb-2.5">
			<div class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md">
				{#if firstName}
					<div class="text-xs absolute left-2.5 top-1 text-lightGray-100/50 dark:text-customGray-100/50">
						{$i18n.t('First Name')}
					</div>
				{/if}
				<input
					class={`px-2.5 text-sm ${firstName ? 'pt-2' : 'pt-0'} w-full h-12 bg-transparent text-lightGray-100 placeholder:text-lightGray-100 dark:text-white dark:placeholder:text-customGray-100 outline-none`}
					placeholder={$i18n.t('First Name')}
					bind:value={firstName}
					required
				/>
			</div>
		</div>
		<div class="flex-1 mb-2.5">
			<div class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md">
				{#if lastName}
					<div class="text-xs absolute left-2.5 top-1 text-lightGray-100/50 dark:text-customGray-100/50">
						{$i18n.t('Last Name')}
					</div>
				{/if}
				<input
					class={`px-2.5 text-sm ${lastName ? 'pt-2' : 'pt-0'} w-full h-12 bg-transparent text-lightGray-100 placeholder:text-lightGray-100 dark:text-white dark:placeholder:text-customGray-100 outline-none`}
					placeholder={$i18n.t('Last Name')}
					bind:value={lastName}
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
						class={`px-2.5 text-sm ${password ? 'pt-2' : 'pt-0'} w-full h-12 bg-transparent text-lightGray-100 placeholder:text-lightGray-100 dark:text-white dark:placeholder:text-customGray-100 outline-none pr-10`}
						type="text"
						bind:value={password}
						placeholder={$i18n.t('Create Password')}
						autocomplete="new-password"
						required
					/>
				{:else}
					<input
						class={`px-2.5 text-sm ${password ? 'pt-2' : 'pt-0'} w-full h-12 bg-transparent text-lightGray-100 placeholder:text-lightGray-100 dark:text-white dark:placeholder:text-customGray-100 outline-none pr-10`}
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
			<Tooltip className="absolute -right-5 md:-right-6 top-3 cursor-pointer" content={$i18n.t('Password must be 8+ characters, with a number, capital letter, and symbol.')}>
				<div class="flex justify-center items-center w-[18px] h-[18px] rounded-full bg-customBlue-600 text-white dark:text-customGray-100 dark:bg-customGray-700">
					<InfoIcon className="size-6"/>
				</div>
			</Tooltip> 
		</div>
		<div class="flex flex-col w-full mb-2.5">
			<div class="relative w-full text-lightGray-100/50 bg-lightGray-300 dark:bg-customGray-900 rounded-md">
				{#if confirmPassword}
					<div class="text-xs absolute left-2.5 top-1 dark:text-customGray-100/50">
						{$i18n.t('Confirm password')}
					</div>
				{/if}
				{#if showConfirmPassword}
					<input
						class={`px-2.5 text-sm ${confirmPassword ? 'pt-2' : 'pt-0'} w-full h-12 bg-transparent text-lightGray-100 placeholder:text-lightGray-100 dark:text-white dark:placeholder:text-customGray-100 outline-none pr-10`}
						type="text"
						bind:value={confirmPassword}
						placeholder={$i18n.t('Confirm Password')}
						autocomplete="new-password"
						required
					/>
				{:else}
					<input
						class={`px-2.5 text-sm ${confirmPassword ? 'pt-2' : 'pt-0'} w-full h-12 bg-transparent text-lightGray-100 placeholder:text-lightGray-100 dark:text-white dark:placeholder:text-customGray-100 outline-none pr-10`}
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
			class=" text-xs w-full h-10 px-3 font-medium py-2 transition rounded-lg {loading
				? ' cursor-not-allowed bg-lightGray-300 hover:bg-lightGray-700 text-lightGray-100 dark:bg-customGray-950 dark:hover:bg-customGray-950 dark:text-white border border-lightGray-400 dark:border-customGray-700'
				: 'bg-lightGray-300 hover:bg-lightGray-700 text-lightGray-100 dark:bg-customGray-900 dark:hover:bg-customGray-950 dark:text-customGray-200 border border-lightGray-400 dark:border-customGray-700'} flex justify-center items-center"
			type="submit"
			disabled={loading}
		>
			{$i18n.t('Register')}
			{#if loading}
				<div class="ml-1.5 self-center">
					<LoaderIcon/>
				</div>
			{/if}
		</button>
	</form>
    <div class="self-center text-xs text-customGray-300 dark:text-customGray-100 pb-5 text-center">By using this service, you agree to our <a href="/">Terms</a> and <a href="/">Conditions</a>.</div>
</div>
