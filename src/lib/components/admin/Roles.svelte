<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';

	import { getRoles, getRoleCapabilities } from '$lib/apis/roles';
	import RoleList from './Roles/RoleList.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	let roles: any[] | null = null;
	let availableCapabilities: string[] = [];

	const fetchData = async () => {
		const [rolesRes, capsRes] = await Promise.allSettled([
			getRoles(localStorage.token),
			getRoleCapabilities(localStorage.token)
		]);

		if (rolesRes.status === 'fulfilled' && rolesRes.value) {
			roles = rolesRes.value.items ?? rolesRes.value;
		} else if (rolesRes.status === 'rejected') {
			toast.error(`${rolesRes.reason}`);
		}

		if (capsRes.status === 'fulfilled' && capsRes.value) {
			const raw = capsRes.value.capabilities ?? capsRes.value;
			// API returns [{key, description}, ...] — extract just the keys
			availableCapabilities = Array.isArray(raw)
				? raw.map((c: any) => (typeof c === 'string' ? c : c.key))
				: [];
		} else if (capsRes.status === 'rejected') {
			toast.error(`${capsRes.reason}`);
		}
	};

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
			return;
		}
		await fetchData();
	});
</script>

<div class="flex flex-col lg:flex-row w-full h-full pb-2">
	<div class="flex-1 px-[16px] overflow-y-scroll">
		<RoleList {roles} {availableCapabilities} onRefresh={fetchData} />
	</div>
</div>
