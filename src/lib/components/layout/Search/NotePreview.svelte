<script lang="ts">
	import { getContext, onDestroy, tick } from 'svelte';
	import { getNoteById } from '$lib/apis/notes';
	import PreviewMarkdown from './PreviewMarkdown.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n: any = getContext('i18n');
	export let id: string;
	export let query = '';
	let content = '';
	let loading = true;
	let error = false;
	let generation = 0;
	let body: HTMLDivElement;
	$: load(id, query);

	async function load(noteId: string, search: string) {
		const version = ++generation;
		loading = true;
		error = false;
		content = '';
		const note = await getNoteById(localStorage.token, noteId).catch(() => null);
		if (version !== generation) return;
		if (note) {
			const terms = search.toLowerCase().split(/\s+/).filter(Boolean);
			const pages = note.data?.pages ?? [];
			const match =
				pages.find(
					(p) =>
						terms.length &&
						terms.every((t) => `${p.title} ${p.content.md}`.toLowerCase().includes(t))
				) ??
				pages.find((p) =>
					terms.some((t) => `${p.title} ${p.content.md}`.toLowerCase().includes(t))
				) ??
				pages[0];
			content = match ? `## ${match.title}\n\n${match.content.md}` : (note.data?.content?.md ?? '');
		} else error = true;
		loading = false;
		await tick();
		if (version !== generation || !body || !search.trim()) return;
		const terms = search.toLowerCase().split(/\s+/).filter(Boolean);
		const walker = document.createTreeWalker(body, NodeFilter.SHOW_TEXT);
		let node: Node | null;
		while ((node = walker.nextNode())) {
			if (terms.some((term) => node!.textContent?.toLowerCase().includes(term))) {
				node.parentElement?.scrollIntoView({ block: 'center' });
				break;
			}
		}
	}
	onDestroy(() => (generation += 1));
</script>

{#if loading}<div class="flex justify-center py-6 text-gray-400">
		<Spinner className="size-4" />
	</div>
{:else if error}<div class="py-4 text-xs text-gray-500 dark:text-gray-400">
		<p>{$i18n.t('Failed to load note preview')}</p>
		<button class="mt-2 underline underline-offset-2" on:click={() => load(id, query)}
			>{$i18n.t('Try again')}</button
		>
	</div>
{:else}<div bind:this={body}>
		<PreviewMarkdown id={`note-search-preview-${id}`} {content} />
	</div>{/if}
