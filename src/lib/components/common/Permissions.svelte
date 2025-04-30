<script lang="ts">
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import Switch from '$lib/components/common/Switch.svelte';

	export let defaultPermissions = {};
	export let permissions = {};

	// Reactive statement to ensure all fields are present in `permissions`
	$: {
		permissions = fillMissingProperties(permissions, defaultPermissions);
	}

	function fillMissingProperties(obj: any, defaults: any) {
		return {
			...defaults,
			...obj,
			workspace: { ...defaults.workspace, ...obj.workspace },
			sharing: { ...defaults.sharing, ...obj.sharing },
			chat: { ...defaults.chat, ...obj.chat },
			features: { ...defaults.features, ...obj.features }
		};
	}

	function formatPermissionName(key: string): string {
		return key
			.split('_')
			.map(word => word.charAt(0).toUpperCase() + word.slice(1))
			.join(' ');
	}

	function formatPermissionCategory(key: string): string {
		return key.charAt(0).toUpperCase() + key.slice(1) + ' Permissions';
	}


	onMount(() => {
		permissions = fillMissingProperties(permissions, defaultPermissions);
	});
</script>

<div>
	{#each Object.entries(permissions) as [categoryName, category], index}
		{#if index !== 0}
			<hr class=" border-gray-100 dark:border-gray-850 my-2" />
		{/if}
		<div>
			<div class=" mb-2 text-sm font-medium">{$i18n.t(formatPermissionCategory(categoryName))}</div>

			{#each Object.entries(category) as [key, value]}
				<div class="flex w-full justify-between my-2 pr-2">
					<div class="self-center text-xs font-medium">
						{$i18n.t(formatPermissionName(key))}
					</div>

					<Switch bind:state={permissions[categoryName][key]} />
				</div>
			{/each}
		</div>
	{/each}
</div>
