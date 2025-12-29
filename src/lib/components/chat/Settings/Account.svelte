<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';

	import { user } from '$lib/stores';
import { updateUserProfile, getSessionUser } from '$lib/apis/auths';
import { getTenantById } from '$lib/apis/tenants';
	import { generateInitialsImage } from '$lib/utils';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import UserProfileImage from './Account/UserProfileImage.svelte';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

let profileImageUrl = '';
let name = '';
let jobTitle = '';
let primaryLocation = '';
let jobDescription = '';
let tenantLogoUrl = '';

	const submitHandler = async () => {
		if (name !== $user?.name) {
			if (profileImageUrl === generateInitialsImage($user?.name) || profileImageUrl === '') {
				profileImageUrl = generateInitialsImage(name);
			}
		}

		const updatedUser = await updateUserProfile(localStorage.token, {
			name: name,
			profile_image_url: profileImageUrl,
			job_title: jobTitle ? jobTitle : null,
			primary_location: primaryLocation ? primaryLocation : null,
			job_description: jobDescription ? jobDescription : null
		}).catch((error) => {
			toast.error(`${error}`);
		});

		if (updatedUser) {
			const sessionUser = await getSessionUser(localStorage.token).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			await user.set(sessionUser);
			if (sessionUser) {
				jobTitle = sessionUser?.job_title ?? '';
				primaryLocation = sessionUser?.primary_location ?? '';
				jobDescription = sessionUser?.job_description ?? '';
				profileImageUrl = sessionUser?.profile_image_url ?? profileImageUrl;
				tenantLogoUrl = sessionUser?.tenant_logo_image_url ?? tenantLogoUrl;
			}
			return true;
		}
		return false;
	};

	onMount(async () => {
		const sessionUser = await getSessionUser(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (sessionUser) {
			name = sessionUser?.name ?? '';
			profileImageUrl = sessionUser?.profile_image_url ?? '';
			jobTitle = sessionUser?.job_title ?? '';
			primaryLocation = sessionUser?.primary_location ?? '';
			jobDescription = sessionUser?.job_description ?? '';
			tenantLogoUrl = sessionUser?.tenant_logo_image_url ?? '';

			if (!tenantLogoUrl && sessionUser?.tenant_id) {
				const tenant = await getTenantById(localStorage.token, sessionUser.tenant_id).catch(
					(error) => {
						console.error(error);
						return null;
					}
				);
				if (tenant?.logo_image_url) {
					tenantLogoUrl = tenant.logo_image_url;
				}
			}
		} else {
			tenantLogoUrl = '';
		}
	});
</script>

<div id="tab-account" class="flex flex-col h-full justify-between text-sm">
	<div class=" overflow-y-scroll max-h-[28rem] md:max-h-full">
		<div class="space-y-1">
			<div>
				<div class="text-base font-medium">{$i18n.t('Your Account')}</div>

				<div class="text-xs text-gray-500 mt-0.5">
					{$i18n.t('Manage your account information.')}
				</div>
			</div>

			<!-- <div class=" text-sm font-medium">{$i18n.t('Account')}</div> -->

			<div class="flex space-x-5 my-4">
				<div class="flex flex-col items-center gap-3">
					<UserProfileImage bind:profileImageUrl user={$user} />
					{#if tenantLogoUrl}
						<div class="flex flex-col items-center space-y-1">
							<div class="max-h-16 max-w-[10rem] rounded-xl border border-gray-100 bg-white px-3 py-2 dark:border-gray-800 dark:bg-gray-900">
								<img
									src={tenantLogoUrl}
									alt={$i18n.t('Tenant Logo')}
									class="max-h-12 w-auto object-contain"
								/>
							</div>
						</div>
					{/if}
				</div>

				<div class="flex flex-1 flex-col">
					<div class=" flex-1 w-full">
						<div class="flex flex-col w-full">
							<div class=" mb-1 text-xs font-medium">{$i18n.t('Name')}</div>

							<div class="flex-1">
								<input
									class="w-full text-sm dark:text-gray-300 bg-transparent outline-hidden"
									type="text"
									bind:value={name}
									required
									placeholder={$i18n.t('Enter your name')}
								/>
							</div>
						</div>

						<div class="flex flex-col w-full mt-2">
							<div class=" mb-1 text-xs font-medium">{$i18n.t('Title')}</div>

							<div class="flex-1">
								<input
									class="w-full text-sm dark:text-gray-300 bg-transparent outline-hidden"
									type="text"
									bind:value={jobTitle}
									maxlength={255}
									placeholder={$i18n.t('Enter your title')}
								/>
							</div>
						</div>

						<div class="flex flex-col w-full mt-2">
							<div class=" mb-1 text-xs font-medium">{$i18n.t('Primary Location')}</div>

							<div class="flex-1">
								<input
									class="w-full text-sm dark:text-gray-300 bg-transparent outline-hidden"
									type="text"
									bind:value={primaryLocation}
									maxlength={255}
									placeholder={$i18n.t('Enter your primary location')}
								/>
							</div>
						</div>

						<div class="flex flex-col w-full mt-2">
							<div class=" mb-1 text-xs font-medium">{$i18n.t('Job Description')}</div>

							<div class="flex-1">
								<Textarea
									className="w-full text-sm dark:text-gray-300 bg-transparent outline-hidden"
									minSize={60}
									maxlength={2500}
									bind:value={jobDescription}
									placeholder={$i18n.t('Describe your role and responsibilities')}
								/>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>

	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			on:click={async () => {
				const res = await submitHandler();

				if (res) {
					saveHandler();
				}
			}}
		>
			{$i18n.t('Save')}
		</button>
	</div>
</div>
