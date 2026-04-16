<script>
	import { getContext, onMount } from 'svelte';
	import { getMyProfile, updateMyProfile } from '$lib/apis/marketplace';
	import { mobile, showSidebar, user } from '$lib/stores';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');
	
	let profile = null;
	let loaded = false;
	let saving = false;
	let skillsText = '';
	let bioText = '';

	onMount(async () => {
		try {
			profile = await getMyProfile(localStorage.token);
		} catch (error) {
			console.error("Failed to load profile", error);
			// Default to Client if doesn't exist yet
			profile = { role: 'Client' };
		}
		loaded = true;
	});

	const saveProfile = async () => {
		saving = true;
		try {
			const parsedSkills = skillsText
				.split(',')
				.map((skill) => skill.trim())
				.filter((skill) => skill.length > 0);

			const res = await updateMyProfile(localStorage.token, {
				role: profile.role,
				skills: parsedSkills,
				bio: bioText
			});
			if (res) {
				toast.success($i18n.t('Profile updated successfully!'));
				profile = res;
				skillsText = Array.isArray(profile.skills) ? profile.skills.join(', ') : '';
				bioText = profile.bio ?? '';
			}
		} catch (error) {
			toast.error(`Error: ${error}`);
		}
		saving = false;
	};

	$: if (loaded && profile) {
		skillsText = Array.isArray(profile.skills) ? profile.skills.join(', ') : '';
		bioText = profile.bio ?? '';
	}
</script>

{#if loaded}
	<div
		class=" flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
			? 'md:max-w-[calc(100%-var(--sidebar-width))]'
			: ''} max-w-full"
	>
		<nav class="   px-2 pt-1.5 backdrop-blur-xl w-full drag-region">
			<div class=" flex items-center">
				{#if $mobile}
					<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center">
						<Tooltip
							content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
							interactive={true}
						>
							<button
								id="sidebar-toggle-button"
								class=" cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition cursor-"
								on:click={() => {
									showSidebar.set(!$showSidebar);
								}}
							>
								<div class=" self-center p-1.5">
									<Sidebar />
								</div>
							</button>
						</Tooltip>
					</div>
				{/if}

				<div class="ml-2 py-0.5 self-center flex items-center justify-between w-full">
					<div class="">
						<div
							class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium bg-transparent py-1 touch-auto pointer-events-auto"
						>
							<span class="min-w-fit transition">
								{$i18n.t('My Marketplace Profile')}
							</span>
						</div>
					</div>

					<div class=" self-center flex items-center gap-1">
						{#if $user !== undefined && $user !== null}
							<UserMenu
								className="w-[240px]"
								role={$user?.role}
								help={true}
							>
								<button
									class="select-none flex rounded-xl p-1.5 w-full hover:bg-gray-50 dark:hover:bg-gray-850 transition"
									aria-label="User Menu"
								>
									<div class=" self-center">
										<img
											src={`${WEBUI_API_BASE_URL}/users/${$user?.id}/profile/image`}
											class="size-6 object-cover rounded-full"
											alt="User profile"
											draggable="false"
										/>
									</div>
								</button>
							</UserMenu>
						{/if}
					</div>
				</div>
			</div>
		</nav>

		<div class=" flex-1 max-h-full overflow-y-auto @container px-4 py-8">
			<div class="max-w-2xl mx-auto">
				<div class="bg-white dark:bg-gray-850 rounded-2xl p-8 mb-8 border border-gray-100 dark:border-gray-800 shadow-sm">
					<h1 class="text-2xl font-bold dark:text-white mb-6">{$i18n.t('Marketplace Settings')}</h1>
					
					<form on:submit|preventDefault={saveProfile} class="space-y-6">
						<div>
							<label class="block text-sm font-medium dark:text-gray-300 mb-2" for="role">
								{$i18n.t('Your Primary Role')}
							</label>
							<p class="text-xs text-gray-500 mb-3">
								Select how you want to participate in the marketplace.
							</p>
							<div class="grid grid-cols-2 gap-4">
								<label class="relative flex cursor-pointer rounded-lg border bg-white p-4 shadow-xs hover:bg-gray-50 dark:bg-gray-900 border-gray-100 dark:border-gray-800 peer-checked:border-blue-500 {profile.role === 'Client' ? 'ring-2 ring-blue-500 border-transparent' : ''}">
									<input type="radio" name="role" value="Client" bind:group={profile.role} class="sr-only">
									<span class="flex flex-col">
										<span class="block text-sm font-medium dark:text-white">Client</span>
										<span class="mt-1 flex items-center text-xs text-gray-500">I want to hire experts.</span>
									</span>
								</label>

								<label class="relative flex cursor-pointer rounded-lg border bg-white p-4 shadow-xs hover:bg-gray-50 dark:bg-gray-900 border-gray-100 dark:border-gray-800 peer-checked:border-blue-500 {profile.role === 'Freelancer' ? 'ring-2 ring-blue-500 border-transparent' : ''}">
									<input type="radio" name="role" value="Freelancer" bind:group={profile.role} class="sr-only">
									<span class="flex flex-col">
										<span class="block text-sm font-medium dark:text-white">Freelancer</span>
										<span class="mt-1 flex items-center text-xs text-gray-500">I want to find works.</span>
									</span>
								</label>
							</div>
						</div>

						<div>
							<label class="block text-sm font-medium dark:text-gray-300 mb-2" for="skills">
								{$i18n.t('Skills')}
							</label>
							<p class="text-xs text-gray-500 mb-2">
								{$i18n.t('Write comma-separated skills, e.g. n8n, API integration, automation')}
							</p>
							<input
								id="skills"
								type="text"
								bind:value={skillsText}
								class="w-full px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-800 bg-transparent dark:text-white focus:outline-hidden focus:ring-2 focus:ring-blue-500"
								placeholder="n8n, Zapier, Backend APIs"
							/>
						</div>

						<div>
							<label class="block text-sm font-medium dark:text-gray-300 mb-2" for="bio">
								{$i18n.t('Bio')}
							</label>
							<textarea
								id="bio"
								bind:value={bioText}
								rows="4"
								class="w-full px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-800 bg-transparent dark:text-white focus:outline-hidden focus:ring-2 focus:ring-blue-500"
								placeholder="Tell clients about your experience and the type of work you do."
							></textarea>
						</div>

						<div class="pt-4 flex justify-end">
							<button
								type="submit"
								disabled={saving}
								class="px-6 py-2 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 rounded-lg transition disabled:opacity-50"
							>
								{saving ? $i18n.t('Saving...') : $i18n.t('Save Settings')}
							</button>
						</div>
					</form>
				</div>
			</div>
		</div>
	</div>
{/if}
