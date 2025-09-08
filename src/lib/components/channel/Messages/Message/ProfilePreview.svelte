<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	import { flyAndScale } from '$lib/utils/transitions';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { getUserActiveStatusById } from '$lib/apis/users';

	export let side = 'right';
	export let align = 'top';

	export let user = null;
	let show = false;

	let active = false;

	const getActiveStatus = async () => {
		const res = await getUserActiveStatusById(localStorage.token, user.id).catch((error) => {
			console.error('Error fetching user active status:', error);
		});

		if (res) {
			active = res.active;
		} else {
			active = false;
		}
	};

	$: if (show) {
		getActiveStatus();
	}
</script>

<DropdownMenu.Root
	bind:open={show}
	closeFocus={false}
	onOpenChange={(state) => {}}
	typeahead={false}
>
	<DropdownMenu.Trigger>
		<slot />
	</DropdownMenu.Trigger>

	<slot name="content">
		<DropdownMenu.Content
			class="max-w-full w-[240px] rounded-lg z-9999 bg-white dark:bg-black dark:text-white shadow-lg"
			sideOffset={8}
			{side}
			{align}
			transition={flyAndScale}
		>
			{#if user}
				<div class=" flex flex-col gap-2 w-full rounded-lg">
					<div class="py-8 relative bg-gray-900 rounded-t-lg">
						<img
							crossorigin="anonymous"
							src={user?.profile_image_url ?? `${WEBUI_BASE_URL}/static/favicon.png`}
							class=" absolute -bottom-5 left-3 size-12 ml-0.5 object-cover rounded-full -translate-y-[1px]"
							alt="profile"
						/>
					</div>

					<div class=" flex flex-col pt-4 pb-2.5 px-4">
						<div class=" -mb-1">
							<span class="font-medium text-sm line-clamp-1"> {user.name} </span>
						</div>

						<div class=" flex items-center gap-2">
							{#if active}
								<div>
									<span class="relative flex size-2">
										<span
											class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"
										/>
										<span class="relative inline-flex rounded-full size-2 bg-green-500" />
									</span>
								</div>

								<div class=" -translate-y-[1px]">
									<span class="text-xs"> {$i18n.t('Active')} </span>
								</div>
							{:else}
								<div>
									<span class="relative flex size-2">
										<span class="relative inline-flex rounded-full size-2 bg-gray-500" />
									</span>
								</div>

								<div class=" -translate-y-[1px]">
									<span class="text-xs"> {$i18n.t('Away')} </span>
								</div>
							{/if}
						</div>
					</div>
				</div>
			{/if}
		</DropdownMenu.Content>
	</slot>
</DropdownMenu.Root>
