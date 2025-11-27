<script lang="ts">
	import { getContext, onMount } from 'svelte';

	const i18n = getContext('i18n');
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';

	export let user = null;
</script>

{#if user}
	<div class=" flex gap-3.5 w-full py-3 px-3 items-center">
		<div class=" items-center flex shrink-0">
			<img
				src={`${WEBUI_API_BASE_URL}/users/${user?.id}/profile/image`}
				class=" size-12 object-cover rounded-xl"
				alt="profile"
			/>
		</div>

		<div class=" flex flex-col w-full flex-1">
			<div class="mb-0.5 font-medium line-clamp-1 pr-2">
				{user.name}
			</div>

			<div class=" flex items-center gap-2">
				{#if user?.active}
					<div>
						<span class="relative flex size-2">
							<span
								class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"
							/>
							<span class="relative inline-flex rounded-full size-2 bg-green-500" />
						</span>
					</div>

					<span class="text-xs"> {$i18n.t('Active')} </span>
				{:else}
					<div>
						<span class="relative flex size-2">
							<span class="relative inline-flex rounded-full size-2 bg-gray-500" />
						</span>
					</div>

					<span class="text-xs"> {$i18n.t('Away')} </span>
				{/if}
			</div>
		</div>
	</div>
{/if}
