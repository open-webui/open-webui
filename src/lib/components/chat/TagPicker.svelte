<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { tags as userTags } from '$lib/stores';
	import {
		addTagById,
		deleteTagById,
		getAllTags,
		getTagsById,
		updateTagColorById
	} from '$lib/apis/chats';
	import { colorDot, tagColor, tagColors, tagDot, type FolderTag } from '$lib/utils/tags';
	import Check from '$lib/components/icons/Check.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');

	/** Search, toggle, create and recolor a chat's tags. Render it inside a menu. */
	export let chatId: string;
	/** The chat's tags; null fetches them when the picker opens. */
	export let assigned: FolderTag[] | null = null;
	export let onChange: (assigned: FolderTag[]) => Promise<void> | void = () => {};

	let query = '';
	// The tag whose color row is open.
	let coloring = '';
	let busy = false;
	let input: HTMLInputElement;

	$: current = assigned ?? [];
	$: needle = query.trim().toLowerCase();
	$: options = [
		...current,
		...(($userTags ?? []) as FolderTag[]).filter(
			(tag) => !current.some((item) => item.id === tag.id)
		)
	].filter((tag) => tag.name.toLowerCase().includes(needle));
	$: canCreate =
		needle &&
		needle !== 'none' &&
		![...current, ...(($userTags ?? []) as FolderTag[])].some(
			(tag) => tag.id === needle.replaceAll(' ', '_') || tag.name.toLowerCase() === needle
		);

	const isAssigned = (tag: FolderTag) => current.some((item) => item.id === tag.id);

	async function mutate(action: () => Promise<FolderTag[]>, reset = false) {
		if (busy) return;
		busy = true;
		try {
			assigned = await action();
			if (reset) query = '';
			$userTags = await getAllTags(localStorage.token);
			await onChange(assigned);
		} catch (error) {
			toast.error(String(error));
		} finally {
			busy = false;
			await tick();
			input?.focus();
		}
	}

	const toggle = (tag: FolderTag) =>
		mutate(() =>
			isAssigned(tag)
				? deleteTagById(localStorage.token, chatId, tag.name)
				: addTagById(localStorage.token, chatId, tag.name)
		);

	onMount(async () => {
		input?.focus();
		try {
			const [all, mine] = await Promise.all([
				getAllTags(localStorage.token),
				assigned ? Promise.resolve(assigned) : getTagsById(localStorage.token, chatId)
			]);
			$userTags = all;
			assigned = mine ?? [];
		} catch (error) {
			toast.error(String(error));
		}
	});
</script>

<form
	on:submit|preventDefault={() => {
		const exact = options.find((tag) => tag.name.toLowerCase() === needle);
		if (exact) void toggle(exact);
		else if (canCreate)
			void mutate(() => addTagById(localStorage.token, chatId, query.trim()), true);
	}}
>
	<input
		bind:this={input}
		class="h-7 w-full bg-transparent px-2 text-xs outline-none placeholder:text-gray-400 dark:placeholder:text-gray-500"
		aria-label={$i18n.t('Find or create a tag')}
		placeholder={$i18n.t('Add tags…')}
		maxlength="64"
		bind:value={query}
		disabled={busy}
	/>
</form>

<div class="max-h-56 overflow-y-auto pt-0.5" role="group" aria-label={$i18n.t('Tags')}>
	{#each options as tag (tag.id)}
		{@const checked = isAssigned(tag)}
		<div
			class="group/tag flex h-[1.6875rem] items-center rounded-xl pr-1 hover:bg-gray-50/60 dark:hover:bg-gray-800/60"
		>
			<button
				type="button"
				role="menuitemcheckbox"
				aria-checked={checked}
				class="flex h-full min-w-0 flex-1 items-center gap-2 px-2 text-[0.8125rem]"
				disabled={busy}
				on:click={() => toggle(tag)}
			>
				<span
					class="mr-1 flex size-3 shrink-0 items-center justify-center rounded-[0.25rem] border transition-colors {checked
						? 'border-gray-800 bg-gray-800 text-white dark:border-gray-100 dark:bg-gray-100 dark:text-gray-900'
						: 'border-gray-300 dark:border-gray-600'}"
				>
					{#if checked}<Check className="size-2" strokeWidth="3.5" />{/if}
				</span>
				<span class="size-1.5 shrink-0 rounded-full {tagDot(tag)}"></span>
				<span class="min-w-0 flex-1 truncate text-left">{tag.name}</span>
			</button>
			{#if checked}
				<button
					type="button"
					class="flex size-5 items-center justify-center rounded-md transition hover:bg-gray-100 focus-visible:opacity-100 group-hover/tag:opacity-100 dark:hover:bg-gray-800 {coloring ===
					tag.id
						? 'opacity-100'
						: 'opacity-0'}"
					aria-label={$i18n.t('Color for {{tag}}', { tag: tag.name })}
					aria-expanded={coloring === tag.id}
					title={$i18n.t('Applies wherever you use this tag')}
					disabled={busy}
					on:click={() => (coloring = coloring === tag.id ? '' : tag.id)}
				>
					<span class="size-2 rounded-full ring-2 ring-white dark:ring-gray-850 {tagDot(tag)}"
					></span>
				</button>
			{/if}
		</div>
		<!-- Colors open inline, so the picker also works inside hover submenus. -->
		{#if checked && coloring === tag.id}
			<div
				class="flex items-center gap-0.5 pb-1 pl-6"
				role="radiogroup"
				aria-label={$i18n.t('Color for {{tag}}', { tag: tag.name })}
			>
				{#each tagColors as color}
					<button
						type="button"
						role="radio"
						aria-checked={tagColor(tag) === color}
						aria-label={$i18n.t(color)}
						title={$i18n.t(color)}
						class="flex size-5 items-center justify-center rounded-md hover:bg-gray-50 dark:hover:bg-gray-800"
						disabled={busy}
						on:click={() =>
							mutate(() => updateTagColorById(localStorage.token, chatId, tag.name, color))}
					>
						<span
							class="size-2 rounded-full {colorDot(color)} {tagColor(tag) === color
								? 'ring-2 ring-gray-300 ring-offset-1 ring-offset-white dark:ring-gray-600 dark:ring-offset-gray-850'
								: ''}"
						></span>
					</button>
				{/each}
			</div>
		{/if}
	{/each}

	{#if canCreate}
		<button
			type="button"
			class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-left text-[0.8125rem] hover:bg-gray-50/60 dark:hover:bg-gray-800/60"
			disabled={busy}
			on:click={() => mutate(() => addTagById(localStorage.token, chatId, query.trim()), true)}
		>
			<Plus className="size-3 text-gray-400" />
			<span class="min-w-0 truncate">{$i18n.t('Create “{{name}}”', { name: query.trim() })}</span>
		</button>
	{:else if !options.length}
		<div class="px-2 py-1.5 text-xs text-gray-400 dark:text-gray-500">
			{$i18n.t('No tags yet. Type to create one.')}
		</div>
	{/if}
</div>
