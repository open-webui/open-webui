<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { user } from '$lib/stores';
	import { getApps, type App } from '$lib/apis/apps';
	import { getChannelAppsById, inviteAppToChannel, removeAppFromChannel } from '$lib/apis/channels';
	export let channel: any;
	let joined: App[] = [];
	let available: App[] = [];
	let selected = '';
	let busy = false;
	$: canManage = channel?.is_manager || $user?.role === 'admin' || channel?.user_id === $user?.id;
	async function load() {
		try {
			joined = await getChannelAppsById(localStorage.token, channel.id);
			available = (await getApps(localStorage.token)).filter(
				(a: App) => a.is_active && !joined.some((j) => j.id === a.id)
			);
		} catch (error) {
			toast.error(String(error));
		}
	}
	async function change(appId: string, remove = false) {
		busy = true;
		try {
			if (remove) {
				await removeAppFromChannel(localStorage.token, channel.id, appId);
			} else {
				await inviteAppToChannel(localStorage.token, channel.id, appId);
			}
			selected = '';
			await load();
		} catch (error) {
			toast.error(String(error));
		} finally {
			busy = false;
		}
	}
	onMount(load);
</script>

<section class="space-y-2 px-1 mt-3" aria-label="Apps">
	<h3 class="text-[0.6875rem] text-gray-400 dark:text-gray-600 dark:text-gray-400">Apps</h3>
	{#each joined as app}
		<div class="flex items-center justify-between gap-2 text-xs text-gray-600 dark:text-gray-400">
			<span
				>{app.name}
				<span class="text-[0.6875rem] text-gray-400 dark:text-gray-600"
					>{app.is_active ? 'App' : 'Inactive'}</span
				></span
			>
			{#if canManage}<button
					type="button"
					disabled={busy}
					class="text-xs text-gray-400 hover:text-red-600 transition disabled:opacity-50"
					on:click={() => change(app.id, true)}>Remove</button
				>{/if}
		</div>
	{:else}<p class="text-[0.6875rem] text-gray-400 dark:text-gray-600">
			No apps have been invited.
		</p>{/each}
	{#if canManage && available.length}
		<div class="flex gap-2">
			<select
				aria-label="App to invite"
				bind:value={selected}
				class="min-w-0 flex-1 bg-transparent text-xs text-gray-600 dark:text-gray-400 outline-hidden"
			>
				<option value="">Choose an app</option>{#each available as app}<option value={app.id}
						>{app.name}</option
					>{/each}
			</select>
			<button
				type="button"
				disabled={!selected || busy}
				on:click={() => change(selected)}
				class="h-7 rounded-lg px-2.5 text-xs bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900 transition hover:bg-black dark:hover:bg-white disabled:opacity-50"
				>Invite</button
			>
		</div>
	{/if}
</section>
