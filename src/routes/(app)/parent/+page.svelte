<script lang="ts">
	import { showSidebar, user } from '$lib/stores';
	import MenuLines from '$lib/components/icons/MenuLines.svelte';
	import { childProfileSync } from '$lib/services/childProfileSync';
	import type { ChildProfile } from '$lib/apis/child-profiles';
	import ChildProfileForm from '$lib/components/profile/ChildProfileForm.svelte';

	let profileSaved = false;

	async function handleProfileSaved(profile: ChildProfile) {
		profileSaved = true;
	}

	async function handleProfileCreated(profile: ChildProfile) {
		profileSaved = true;
	}

	async function handleChildSelected(profile: ChildProfile, index: number) {
		await childProfileSync.setCurrentChildId(profile.id);
	}

</script>

<svelte:head>
	<title>Add Child - Parent View</title>
</svelte:head>

<div
	class="flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-260px)]'
		: ''} max-w-full"
>
	<nav
		class="px-2.5 pt-1.5 pb-2 backdrop-blur-xl w-full drag-region bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800"
	>
		<div class="flex items-center justify-between">
			<div class="flex items-center">
				<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center self-end">
					<button
						id="sidebar-toggle-button"
						class="cursor-pointer p-1.5 flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition"
						on:click={() => {
							showSidebar.set(!$showSidebar);
						}}
						aria-label="Toggle Sidebar"
					>
						<div class="m-auto self-center">
							<MenuLines />
						</div>
					</button>
				</div>
				<div class="flex w-full">
					<div class="flex items-center text-xl font-semibold">Add Child View</div>
				</div>
			</div>
		</div>
	</nav>

	<ChildProfileForm
		showResearchFields={false}
		requireResearchFields={false}
		showPersonalityTraits={false}
		onProfileCreated={handleProfileCreated}
		onProfileSaved={handleProfileSaved}
		onChildSelected={handleChildSelected}
	/>
</div>
