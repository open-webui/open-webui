<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { getNoteById } from '$lib/apis/notes';
	import { getUserInfoById } from '$lib/apis/users';
	import { capitalizeFirstLetter } from '$lib/utils';

	const i18n = getContext('i18n');

	export let noteId: string;
	export let href: string;

	let title = '';
	let author = '';
	let loading = true;

	onMount(async () => {
		try {
			const note = await getNoteById(localStorage.token, noteId);
			if (note) {
				title = note.title || $i18n.t('Untitled');

				if (note.user_id) {
					try {
						const userInfo = await getUserInfoById(localStorage.token, note.user_id);
						if (userInfo) {
							author = capitalizeFirstLetter(userInfo.name ?? userInfo.email ?? '');
						}
					} catch {
						// user lookup failed, skip author
					}
				}
			}
		} catch {
			title = $i18n.t('Note');
		} finally {
			loading = false;
		}
	});
</script>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-static-element-interactions -->
<button
	class="relative group py-2 px-3 w-60 flex flex-col bg-white dark:bg-gray-850 border border-gray-50/30 dark:border-gray-800/30 rounded-xl text-left cursor-pointer"
	type="button"
	on:click|preventDefault|stopPropagation={() => {
		try {
			const url = new URL(href, window.location.origin);
			goto(url.pathname);
		} catch {
			// fallback
		}
	}}
>
	<div class="flex flex-col justify-center w-full min-w-0">
		<div class="dark:text-gray-100 text-sm flex justify-between items-center gap-2">
			<div class="font-medium line-clamp-1 flex-1 min-w-0">
				{#if loading}
					<span class="text-gray-400">...</span>
				{:else}
					{title}
				{/if}
			</div>
			<div class="text-gray-500 text-xs shrink-0">{$i18n.t('Note')}</div>
		</div>
		{#if author}
			<div class="text-gray-500 text-xs line-clamp-1 mt-0.5">
				{$i18n.t('By {{name}}', { name: author })}
			</div>
		{/if}
	</div>
</button>
