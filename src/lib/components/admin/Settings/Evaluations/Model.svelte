<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import ArenaModelModal from './ArenaModelModal.svelte';
	export let model;

	let showModel = false;
</script>

<ArenaModelModal
	bind:show={showModel}
	edit={true}
	{model}
	on:submit={async (e) => {
		dispatch('edit', e.detail);
	}}
	on:delete={async () => {
		dispatch('delete');
	}}
/>

<div class="group p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-md hover:border-gray-300 dark:hover:border-gray-600 transition-all duration-200">
	<div class="flex justify-between items-center gap-3">
		<!-- Model Info -->
		<div class="flex items-center gap-3 flex-1 min-w-0">
			<!-- Profile Image -->
			<div class="flex-shrink-0">
				<div class="w-12 h-12 rounded-xl overflow-hidden ring-2 ring-gray-200 dark:ring-gray-700 group-hover:ring-blue-500 transition-all duration-200">
					<img
						src={model.meta.profile_image_url}
						alt={model.name}
						class="w-full h-full object-cover"
					/>
				</div>
			</div>

			<!-- Text Info -->
			<div class="flex-1 min-w-0">
				<h3 class="font-semibold text-sm text-gray-900 dark:text-gray-100 line-clamp-1 mb-0.5">
					{model.name}
				</h3>
				<p class="text-xs text-gray-500 dark:text-gray-400 line-clamp-1">
					{model?.meta?.description ?? model.id}
				</p>
			</div>
		</div>

		<!-- Settings Button -->
		<div class="flex-shrink-0">
			<button
				class="p-2.5 rounded-lg text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 transition-all duration-200 group-hover:bg-gray-100 dark:group-hover:bg-gray-700"
				type="button"
				on:click={() => {
					showModel = true;
				}}
			>
				<Cog6 className="size-4" />
			</button>
		</div>
	</div>
</div>