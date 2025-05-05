<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { getPermissions } from '$lib/apis/permissions';

	const i18n = getContext('i18n');

	import Switch from '$lib/components/common/Switch.svelte';
	import { toast } from 'svelte-sonner';

	export let defaultPermissions = {};
	export let permissions = {};

	let allPermissions = [];
	let loading = true;

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
		// Find a permission with a matching name in allPermissions
		const permission = Array.isArray(allPermissions) && allPermissions.find((p) => p.name === key);

		// Return the label
		return permission.label;
	}

	function formatPermissionCategory(key: string): string {
		return key.charAt(0).toUpperCase() + key.slice(1) + ' Permissions';
	}

	onMount(async () => {
		permissions = fillMissingProperties(permissions, defaultPermissions);

		try {
			const result = await getPermissions(localStorage.token);
			if (Array.isArray(result) && result.length > 0) {
				allPermissions = result;
			} else {
				console.error('getPermissions returned empty or invalid data', result);
				toast.error('Failed to load permission data');
			}
		} catch (error) {
			console.error('Error loading permissions:', error);
			toast.error(`Failed to load permissions: ${error}`);
		} finally {
			loading = false;
		}
	});
</script>

<div>
	{#if loading}
		<div class="flex justify-center py-4">
			<span class="text-sm">Loading permissions...</span>
		</div>
	{:else}
		{#each Object.entries(permissions) as [categoryName, category], index}
			{#if index !== 0}
				<hr class=" border-gray-100 dark:border-gray-850 my-2" />
			{/if}
			<div>
				<div class=" mb-2 text-sm font-medium">
					{$i18n.t(formatPermissionCategory(categoryName))}
				</div>

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
	{/if}
</div>
