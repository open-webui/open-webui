<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { createEventDispatcher, getContext, onMount } from 'svelte';

	import { flyAndScale } from '$lib/utils/transitions';
	import { goto } from '$app/navigation';
	import ArchiveBox from '$lib/components/icons/ArchiveBox.svelte';
	import { showSettings, showCompanySettings, activeUserIds, USAGE_POOL, mobile, showSidebar } from '$lib/stores';
	import { fade, slide } from 'svelte/transition';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { userSignOut } from '$lib/apis/auths';
	import SettingsIcon from '$lib/components/icons/SettingsIcon.svelte';
	import SignOutIcon from '$lib/components/icons/SignOutIcon.svelte';
	import CompanySettingsIcon from '$lib/components/icons/CompanySettingsIcon.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let className = 'max-w-[15rem]';

	const dispatch = createEventDispatcher();
</script>

<DropdownMenu.Root
	bind:open={show}
	onOpenChange={(state) => {
		dispatch('change', state);
	}}
>
	<DropdownMenu.Trigger>
		<div class="text-2xs bg-lightGray-700 py-2 px-2 rounded-lg">{$i18n.t('Filter by category')}</div>
	</DropdownMenu.Trigger>

		<DropdownMenu.Content
			class="w-full {className} min-h-[8rem] p-3 text-sm rounded-lg border border-lightGray-400 dark:border-customGray-700 px-1 py-1.5 z-50 bg-lightGray-300 dark:bg-customGray-900 dark:text-white shadow-lg font-primary"
			sideOffset={8}
			side="bottom"
			align="start"
			transition={(e) => fade(e, { duration: 100 })}
		>
			<slot/>

			
		</DropdownMenu.Content>
	
</DropdownMenu.Root>
