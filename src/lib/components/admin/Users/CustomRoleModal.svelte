<script lang="ts">
	import { getContext } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { getCustomRolePermissionCatalog } from '$lib/apis/users';

	const i18n: any = getContext('i18n');
	export let show = false;
	export let role: any = null;
	export let onSubmit: (data: any) => Promise<void> = async () => {};

	let name = '';
	let displayName = '';
	let permissions: Record<string, any> = {};
	let catalog: Record<string, any> = {};
	let catalogLoading = false;
	let catalogError = '';
	let initializedRole = '';
	let saving = false;

	$: if (show && initializedRole !== (role?.id ?? 'new')) {
		initializedRole = role?.id ?? 'new';
		init();
	}
	$: if (!show) initializedRole = '';

	const cloneContract = (value: any): any =>
		Object.fromEntries(
			Object.entries(value ?? {}).map(([key, child]) => [
				key,
				typeof child === 'object' && child !== null ? cloneContract(child) : false
			])
		);
	const flatten = (value: any, prefix = ''): { path: string; label: string; section: string }[] =>
		Object.entries(value ?? {}).flatMap(([key, child]) => {
			const path = prefix ? `${prefix}.${key}` : key;
			return typeof child === 'object' && child !== null
				? flatten(child, path)
				: [
						{
							path,
							label: key.replaceAll('_', ' '),
							section: prefix.split('.')[0] || 'Permissions'
						}
					];
		});
	$: permissionEntries = flatten(catalog);
	$: sections = [...new Set(permissionEntries.map((entry) => entry.section))];

	const setPermission = (path: string, value: boolean) => {
		const keys = path.split('.');
		let target = permissions;
		keys.slice(0, -1).forEach((key) => (target = target[key] ??= {}));
		target[keys.at(-1) as string] = value;
		permissions = { ...permissions };
	};
	const getPermission = (path: string) =>
		(path.split('.').reduce((value: any, key) => value?.[key], permissions) as any) === true;

	const init = async () => {
		name = role?.name ?? '';
		displayName = role?.display_name ?? '';
		catalogLoading = true;
		catalogError = '';
		try {
			const response = await getCustomRolePermissionCatalog(localStorage.token);
			catalog = response?.permissions ?? response?.catalog ?? response ?? {};
			permissions = cloneContract(catalog);
			for (const entry of flatten(role?.permissions ?? {}))
				setPermission(entry.path, getPermissionFrom(role.permissions, entry.path));
		} catch (error) {
			catalogError = `${error}`;
		} finally {
			catalogLoading = false;
		}
	};
	const getPermissionFrom = (value: any, path: string) =>
		path.split('.').reduce((current, key) => current?.[key], value) === true;

	const submit = async () => {
		saving = true;
		try {
			await onSubmit({ name, display_name: displayName, permissions });
			show = false;
		} finally {
			saving = false;
		}
	};
</script>

<Modal size="lg" bind:show>
	<div class="max-h-[85vh] overflow-y-auto px-5 pb-5 dark:text-gray-200">
		<div class="flex items-center justify-between py-3">
			<h2 class="text-sm font-medium">
				{role ? $i18n.t('Edit Custom Role') : $i18n.t('New Custom Role')}
			</h2>
			<button
				class="rounded-lg p-1 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
				aria-label={$i18n.t('Close')}
				on:click={() => (show = false)}
			>
				<XMark className="size-4" />
			</button>
		</div>
		<form class="space-y-4" on:submit|preventDefault={submit}>
			<div class="grid gap-3 sm:grid-cols-2">
				<label class="block text-xs text-gray-500"
					>{$i18n.t('Internal name')}
					<input
						class="mt-1 w-full rounded-lg bg-transparent px-2.5 py-2 text-sm ring-1 ring-gray-200 outline-hidden dark:ring-gray-700"
						bind:value={name}
						disabled={!!role}
						required
						pattern="[a-z0-9_-]+"
						aria-describedby="role-name-help"
					/>
					<span id="role-name-help" class="mt-1 block text-[11px]"
						>{$i18n.t('Lowercase letters, numbers, hyphens, and underscores.')}</span
					>
				</label>
				<label class="block text-xs text-gray-500"
					>{$i18n.t('Display name')}
					<input
						class="mt-1 w-full rounded-lg bg-transparent px-2.5 py-2 text-sm ring-1 ring-gray-200 outline-hidden dark:ring-gray-700"
						bind:value={displayName}
						required
						maxlength="128"
					/>
				</label>
			</div>
			<div class="border-t border-gray-100 pt-3 dark:border-gray-800">
				<div class="mb-3 text-xs text-gray-500">{$i18n.t('Permissions')}</div>
				{#if catalogLoading}<Spinner className="size-5" />{:else if catalogError}<div
						class="rounded-lg bg-red-50 p-3 text-xs text-red-700 dark:bg-red-950/30 dark:text-red-300"
						role="alert"
					>
						{$i18n.t('Could not load the permission catalog')}: {catalogError}
					</div>{:else if permissionEntries.length === 0}<div class="text-xs text-gray-500">
						{$i18n.t('No permissions are available.')}
					</div>{:else}
					<div class="grid gap-4 sm:grid-cols-2">
						{#each sections as section}<fieldset>
								<legend class="mb-2 text-sm font-medium capitalize"
									>{section.replaceAll('_', ' ')}</legend
								>
								<div class="space-y-2">
									{#each permissionEntries.filter((entry) => entry.section === section) as entry}<label
											class="flex items-center justify-between gap-3 text-xs capitalize text-gray-600 dark:text-gray-300"
											><span>{entry.label}</span><input
												type="checkbox"
												checked={getPermission(entry.path)}
												on:change={(event) =>
													setPermission(entry.path, event.currentTarget.checked)}
												aria-label={entry.path}
											/></label
										>{/each}
								</div>
							</fieldset>{/each}
					</div>
				{/if}
			</div>
			<div class="flex justify-end gap-2 border-t border-gray-100 pt-4 dark:border-gray-800">
				<button
					type="button"
					class="rounded-full px-3.5 py-1.5 text-sm hover:bg-gray-100 dark:hover:bg-gray-800"
					on:click={() => (show = false)}>{$i18n.t('Cancel')}</button
				>
				<button
					type="submit"
					disabled={saving || catalogLoading || !!catalogError || permissionEntries.length === 0}
					class="rounded-full bg-black px-3.5 py-1.5 text-sm text-white disabled:opacity-50 dark:bg-white dark:text-black"
					>{saving ? $i18n.t('Saving') : $i18n.t('Save')}</button
				>
			</div>
		</form>
	</div>
</Modal>
