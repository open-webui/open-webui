<script lang="ts">
	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import IonosLogo from '$lib/IONOS/components/icons/IonosLogo.svelte';

	import {
		user
	} from '$lib/stores';
</script>

<nav class="sticky top-0 z-30 w-full px-1.5 py-4 -mb-8 flex items-center drag-region">
	<div class=" flex max-w-full w-full mx-auto px-1 pt-0.5 bg-transparent">
		<div class="flex justify-between items-center w-full max-w-full">
			<div
				class="items-center flex h-10 overflow-hidden py-0.5"
			>
				<a href="/">
					<IonosLogo className={"h-6"} />
				</a>
			</div>

			<div class="self-start flex flex-none items-center text-gray-600 dark:text-gray-400">
				{#if $user !== undefined}
					<UserMenu
						className="max-w-[200px]"
						role={$user?.role}
					>
						<button
							class="select-none flex rounded-xl p-1.5 w-full hover:bg-gray-50 dark:hover:bg-gray-850 transition"
							aria-label="User Menu"
						>
							<div class=" self-center">
								<img
									src={$user?.profile_image_url}
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

<content class="block mt-10 mx-3">
	<slot />
</content>

<style>
</style>
