<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';

	import { user, config, settings, company, companyConfig } from '$lib/stores';
	import { updateUserProfile, createAPIKey, getAPIKey, deleteUserProfile, updateCompanyConfig, getCompanyConfig, updateCompanyDetails } from '$lib/apis/auths';
	import { getGravatarUrl } from '$lib/apis/utils';
	import { generateInitialsImage, canvasPixelTest } from '$lib/utils';
	import { copyToClipboard } from '$lib/utils';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import CameraIcon from '$lib/components/icons/CameraIcon.svelte';
	import DeleteIcon from '$lib/components/icons/DeleteIcon.svelte';
	import { updateUserPassword } from '$lib/apis/auths';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import DOMPurify from 'dompurify';
	import Switch from '$lib/components/common/Switch.svelte';
	import WebSearchIcon from '$lib/components/icons/WebSearchIcon.svelte';
	import ImageGenerateIcon from '$lib/components/icons/ImageGenerateIcon.svelte';
	import CodeInterpreterIcon from '$lib/components/icons/CodeInterpreterIcon.svelte';
	import { onClickOutside } from '$lib/utils';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import LoaderIcon from '$lib/components/icons/LoaderIcon.svelte';
	import LinkEditor from './LinkEditor.svelte';
	import OnBoarding from '$lib/components/OnBoarding.svelte';

	const i18n = getContext('i18n');

	export let saveHandler: Function;
	export let saveSettings: Function;

	let profileImageUrl = '';
	let companyName = '';
	let loading = false;

	let hideModelLogo = false;

	
	let profileImageInputElement: HTMLInputElement;

	let showDeleteConfirm = false;

	let userPermissions = {
		websearch: false,
		image_generation: false,
		// code_interpreter: false,
		// audio: false
	};

	const userPermissionsIcons = {
		websearch: WebSearchIcon,
		image_generation: ImageGenerateIcon,
		// code_interpreter: CodeInterpreterIcon,
	};

	const userPermissionsText = {
		websearch: "Web Search",
		image_generation: "Image Gen",
		// code_interpreter: "Code Interpreter",
		// audio: "Audio In and Out"
	}

	let showUserPermissionsDropdown = false;
	let userPermissionsRef;

	let showChatLifetimeDropdown = false;
	let chatLifetimeDropdownRef;

	const chatLifetimeOptions = [{value: 30, label: '30 days'}, {value: 91, label: '3 months'}, {value: 183, label: '6 months'}, {value: 275, label: '9 months'}, {value: 365, label: '1 year'}, {value: 0, label: "no limit"}];
	let chatLifetime = chatLifetimeOptions[5];

	let userNotice = '';


	const deleteUserHandler = async () => {
		const userId = $user.id;
		await deleteUserProfile(localStorage.token, userId);
	}

	onMount(async () => {
		companyName = $company?.name;
		profileImageUrl = $company?.profile_image_url;	
		if($companyConfig?.config?.ui?.hide_model_logo_in_chat) {
			hideModelLogo = $companyConfig?.config?.ui?.hide_model_logo_in_chat;
		}
		if($companyConfig?.config?.rag?.web?.search?.enable){
			userPermissions = {
				...userPermissions,
				websearch: $companyConfig?.config?.rag?.web?.search?.enable,
			};
		if($companyConfig?.config?.image_generation?.enable) {
			userPermissions = {
				...userPermissions,
				image_generation: $companyConfig?.config?.image_generation?.enable
			};
		}
		// if($companyConfig?.config?.ui?.custom_user_notice) {
		// 	userNotice = $companyConfig?.config?.ui?.custom_user_notice;
		// }
	}});
	$: console.log(userNotice, 'user notice')

	const onSubmit = async () => {
		loading = true;

		const promises = [];
		let companyInfo = null;
		let companyConfigInfo = null;

		if (companyName !== $company.name || profileImageUrl !== $company?.profile_image_url) {
			const companyPromise = updateCompanyDetails(localStorage.token, companyName, profileImageUrl)
				.then((res) => {
					companyInfo = res;
				})
				.catch((error) => {
					toast.error(`${error}`);
				});
			promises.push(companyPromise);
		}

		const configPromise = updateCompanyConfig(
			localStorage.token,
			hideModelLogo,
			chatLifetimeOptions?.value,
			userNotice,
			userPermissions?.websearch,
			userPermissions?.image_generation
		)
			.then((res) => {
				companyConfigInfo = res;
			})
			.catch((error) => {
				toast.error(`${error}`);
			});
		promises.push(configPromise);

		await Promise.all(promises);

		if (companyInfo) {
			company.set(companyInfo);
		}

		if (companyConfigInfo) {
			toast.success($i18n.t('Updated successfuly'));
			companyConfig.set(companyConfigInfo);
		}

		loading = false;
	}
</script>

<!-- space-y-3 overflow-y-scroll max-h-[28rem] lg:max-h-full -->
<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Are you sure you want to delete account?')}
	on:confirm={() => {
		deleteUserHandler();
	}}
	confirmLabel={$i18n.t('Delete Account')}
	>
	<div class=" text-sm text-gray-700 dark:text-gray-300 flex-1 line-clamp-3">
		{@html DOMPurify.sanitize(
			$i18n.t('This action is permanent and cannot be undone. All your data will be lost.')
		)}
	</div>
</DeleteConfirmDialog>
<div class="flex flex-col justify-between text-sm pt-5">
	<div class=" ">
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

		<div class="mb-5">
			<!-- <div class=" text-sm font-medium">{$i18n.t('Account')}</div> -->

			<div class="flex space-x-5">
				<div class="flex flex-col">
					<div class="self-center mt-2">
						<button
							class="relative rounded-full dark:bg-gray-700"
							type="button"
							on:click={() => {
								profileImageInputElement.click();
							}}
						>
							<img
								src={profileImageUrl !== '' ? profileImageUrl : generateInitialsImage(companyName)}
								alt="profile"
								class=" rounded-lg size-16 object-cover"
							/>

							<div
								class="absolute flex justify-center rounded-full bottom-0 left-0 right-0 top-0 h-full w-full overflow-hidden bg-gray-700 bg-fixed opacity-0 transition duration-300 ease-in-out hover:opacity-50"
							>
								<div class="my-auto text-gray-100">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 20 20"
										fill="currentColor"
										class="w-5 h-5"
									>
										<path
											d="m2.695 14.762-1.262 3.155a.5.5 0 0 0 .65.65l3.155-1.262a4 4 0 0 0 1.343-.886L17.5 5.501a2.121 2.121 0 0 0-3-3L3.58 13.419a4 4 0 0 0-.885 1.343Z"
										/>
									</svg>
								</div>
							</div>
						</button>
					</div>
				</div>

				<div class="flex-1 flex flex-col self-center gap-0.5 mb-5">
					<div class=" mb-0.5 text-sm dark:text-customGray-100">{$i18n.t('Profile Picture')}</div>
					<div class="text-xs dark:text-customGray-100/50 mb-2">
						{$i18n.t('We only support PNGs, JPEGs and GIFs under 10MB')}
					</div>

					<div class="flex items-center">
						<button
							type="button"
							on:click={() => {
								profileImageInputElement.click();
							}}
							class="flex items-center font-medium text-xs dark:text-customGray-300 px-2 py-1 rounded-xl border border-customGray-700 dark:bg-customGray-900"
						>
							<CameraIcon className="size-4 mr-1" />
							{$i18n.t('Upload Image')}
						</button>
						
						<button
							class="flex items-center text-xs text-center text-gray-800 text-2xs dark:text-customGray-300 rounded-lg px-2 py-1"
							on:click={async () => {
								profileImageUrl = '/user.png';
							}}
							><DeleteIcon className="mr-1 size-4" />
							{$i18n.t('Remove')}</button
						>
					</div>
				</div>
			</div>

			<div class="pt-0.5">
				<div class="flex flex-col w-full mb-2.5">
					<div class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md">
						{#if companyName}
							<div class="text-xs absolute left-2.5 top-1 text-lightGray-100/50 dark:text-customGray-100/50">
								{$i18n.t('Name')}
							</div>
						{/if}
						<input
							class={`px-2.5 text-sm ${companyName ? 'pt-2' : 'pt-0'} text-lightGray-100 placeholder:text-lightGray-100 w-full h-12 bg-transparent dark:text-customGray-100 dark:placeholder:text-customGray-100 outline-none`}
							placeholder={$i18n.t(' Name')}
							bind:value={companyName}
						/>
					</div>
				</div>
				<div class="mb-2.5">
					<div class="flex items-center justify-between mb-1 w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md h-12 px-2.5 py-2">
						
							<div class="text-sm text-lightGray-100 dark:text-customGray-100">
								{$i18n.t('Hide model logo in chat')}
							</div>
		
						<div class="flex items-center">
							{#if hideModelLogo}
								<div class="text-xs text-lightGray-100/50 dark:text-customGray-100/50 mr-2">On</div>
							{:else}
								<div class="text-xs text-lightGray-100/50 dark:text-customGray-100/50 mr-2">Off</div>
							{/if}
							<Switch
								bind:state={hideModelLogo}
							/>
						</div>
					</div>
				</div>	
				<span class="text-xs text-lightGray-100/50 dark:text-customGray-100/50">{$i18n.t('Hide the model logo in chat responses and show workspace logo instead')}</span>
			</div>	
		</div>
		
		<div>
			<div
				class="flex w-full justify-between items-center py-2.5 border-b border-lightGray-400 dark:border-customGray-700 mb-2.5"
			>
				<div class="flex w-full justify-between items-center">
					<div class="text-xs text-lightGray-100 dark:text-customGray-300">{$i18n.t('User permissions')}</div>
				</div>
			</div>
			<div class="mb-2.5" use:onClickOutside={() => (showUserPermissionsDropdown = false)}>
				<div class="relative" bind:this={userPermissionsRef}>
					<button
						type="button"
						class="flex items-center justify-between w-full text-sm h-12 px-3 py-2 {
							showUserPermissionsDropdown ? 'border' : ''
						} border-lightGray-400 dark:border-customGray-700 rounded-md bg-lightGray-300 dark:bg-customGray-900 cursor-pointer"
						on:click={() => (showUserPermissionsDropdown = !showUserPermissionsDropdown)}
					>
						<span class="text-lightGray-100 dark:text-customGray-100">{$i18n.t('User Permissions')}</span>
						<div class="flex items-center">
							<div class="text-xs text-lightGray-100/50 dark:text-customGray-100/50 max-w-[15rem] text-left">
								{Object.keys(userPermissions)?.filter(item => userPermissions?.[item]).map(el => userPermissionsText[el]).join(', ')}
							</div>
						<ChevronDown className="size-3 ml-1" />
						</div>
					</button>
			
					{#if showUserPermissionsDropdown}
						<div
							class="max-h-60 pb-1 overflow-y-auto absolute z-50 w-full -mt-1 bg-lightGray-300 dark:bg-customGray-900 border-l border-r border-b border-lightGray-400 dark:border-customGray-700 rounded-b-md"
						>
							<hr class="border-t border-lightGray-400 dark:border-customGray-700 mb-2 mt-1 mx-0.5" />
							<div class="px-1">
								{#each Object.keys(userPermissions) as permission}
									<div
										role="button"
										tabindex="0"
										class="flex items-center rounded-xl w-full justify-between px-3 py-2 hover:bg-lightGray-700 dark:hover:bg-customGray-950 cursor-pointer text-sm dark:text-customGray-100"
									>
										<div class="flex items-center gap-2">
											{#if userPermissionsIcons?.[permission]}
												<svelte:component
													this={userPermissionsIcons?.[permission]}
													className="size-4"
												/>
											{/if}
											<span class="capitalize">{permission.replace(/_/g, ' ')}</span>
										</div>
										<Checkbox
											state={userPermissions?.[permission] ? 'checked' : 'unchecked'}
											on:change={(e) => {
												e.stopPropagation();
												userPermissions[permission] = e.detail === 'checked';
											}}
										/>
									</div>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			</div>
		</div>

		<div>
			<div
				class="flex w-full justify-between items-center py-2.5 border-b border-lightGray-400 dark:border-customGray-700 mb-2.5"
			>
				<div class="flex w-full justify-between items-center">
					<div class="text-xs text-lightGray-100 dark:text-customGray-300">{$i18n.t('Safety & Compliance')}</div>
				</div>
			</div>
			<div class="mb-2.5" use:onClickOutside={() => (showChatLifetimeDropdown = false)}>
				<div class="relative" bind:this={chatLifetimeDropdownRef}>
					<button
						type="button"
						class={`flex items-center justify-between w-full text-sm h-12 px-3 py-2 ${
							showChatLifetimeDropdown ? 'border' : ''
						} border-lightGray-400 dark:border-customGray-700 rounded-md bg-lightGray-300 dark:bg-customGray-900 cursor-pointer`}
						on:click={() => {
							showChatLifetimeDropdown = !showChatLifetimeDropdown
							}}
					>
						<span class="text-lightGray-100 dark:text-customGray-100"
							>{$i18n.t('How long should chats be saved')}</span
						>
						
						<div class="flex items-center gap-2 text-xs text-lightGray-100 dark:text-customGray-100/50">
							{chatLifetime.label}
							<ChevronDown className="size-3" />
						</div>
						
					</button>

					{#if showChatLifetimeDropdown}
						<div
							class="max-h-40 overflow-y-auto absolute z-50 w-full -mt-1 bg-lightGray-300 pb-1 dark:bg-customGray-900 border-l border-r border-b border-lightGray-400 dark:border-customGray-700 rounded-b-md"
						>
							<hr class="border-t border-lightGray-400 dark:border-customGray-700 mb-2 mt-1 mx-0.5" />
							<div class="px-1">
								{#each chatLifetimeOptions as option}
									<button
										class="px-3 py-2 flex items-center gap-2 w-full rounded-xl text-sm hover:bg-lightGray-700 dark:hover:bg-customGray-950 dark:text-customGray-100 cursor-pointer text-gray-900"
										on:click={() => {
											chatLifetime = option;
											showChatLifetimeDropdown = false;
										}}
									>
										{$i18n.t(option.label)}
									</button>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			</div>
			<!-- <div class="flex flex-col w-full mb-2.5">
				<div class="relative w-full dark:bg-customGray-900 rounded-md">
					{#if userNotice}
						<div class="text-xs absolute left-2.5 top-1 dark:text-customGray-100/50">
							{$i18n.t('User notice')}
						</div>
					{/if}
					<input
						class={`px-2.5 text-sm ${userNotice ? 'mt-2' : 'mt-0'} w-full h-10 bg-transparent dark:text-customGray-100 dark:placeholder:text-customGray-100 outline-none`}
						placeholder={$i18n.t('User notice')}
						bind:value={userNotice}
					/>
				</div>
			</div> -->
			<LinkEditor on:updateContent={(e) => userNotice = e.detail}/>
			<!-- <LinkEditor bind:text={userNotice} label={$i18n.t('User notice')}/> -->
			<span class="text-xs text-lightGray-100/50 dark:text-customGray-100/50">
				{$i18n.t('The disclaimer is displayed at the bottom of the user interface')}
			</span>
		</div>
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class=" text-xs w-[168px] h-10 px-3 py-2 transition rounded-lg {loading
				? ' cursor-not-allowed bg-lightGray-300 border-lightGray-400 text-lightGray-100 font-medium hover:bg-lightGray-550 dark:bg-customGray-950 dark:hover:bg-customGray-950 dark:text-white border dark:border-customGray-700'
				: 'bg-lightGray-300 border-lightGray-400 text-lightGray-100 font-medium hover:bg-lightGray-550 dark:bg-customGray-900 dark:hover:bg-customGray-950 dark:text-customGray-200 border dark:border-customGray-700'} flex justify-center items-center"
			type="button"
			disabled={loading}
			on:click={onSubmit}
		>
			{$i18n.t('Save')}
			{#if loading}
				<div class="ml-1.5 self-center">
					<LoaderIcon />
				</div>
			{/if}
		</button>
	</div>
	<div class="flex w-full justify-between items-center py-2.5 border-b border-lightGray-400 dark:border-customGray-700 mb-2">
		<div class="flex w-full justify-between items-center">
			<div class="text-xs text-lightGray-100 dark:text-customGray-300">{$i18n.t('Delete account')}</div>
		</div>
	</div>
	<div class="flex justify-between items-start pt-3 pb-5">
		<button type="button" class="flex items-center text-xs text-[#F65351]" on:click={() => {
			showDeleteConfirm = true;
		}}>
			<DeleteIcon className="mr-1 size-4" />
			{$i18n.t('Delete account')}
		</button>
		<div class="shrink-0 w-[218px] dark:text-customGray-100/50 text-xs">
			{$i18n.t('This action is not reversible, so please continue with caution.')}
		</div>
	</div>
</div>
