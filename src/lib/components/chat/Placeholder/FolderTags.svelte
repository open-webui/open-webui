<script lang="ts">
	import { getContext, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { tags as userTags } from '$lib/stores';
	import { addTagById, deleteTagById, getAllTags, updateTagColorById } from '$lib/apis/chats';
	import type { WorkspaceChat } from '$lib/utils/folders';
	import { colorDot, tagColor, tagColors, tagDot, type FolderTag } from '$lib/utils/tags';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');

	export let chat: WorkspaceChat;
	export let max = 2;
	export let onChange: () => Promise<void> = async () => {};

	let show = false;
	let query = '';
	let busy = false;
	let input: HTMLInputElement;
	let assigned: FolderTag[] = [];

	$: assigned = chat.tags ?? [];
	$: needle = query.trim().toLowerCase();
	$: options = [
		...assigned,
		...(($userTags ?? []) as FolderTag[]).filter(
			(tag) => !assigned.some((item) => item.id === tag.id)
		)
	].filter((tag) => tag.name.toLowerCase().includes(needle));
	$: canCreate =
		needle &&
		needle !== 'none' &&
		![...assigned, ...(($userTags ?? []) as FolderTag[])].some(
			(tag) => tag.id === needle.replaceAll(' ', '_') || tag.name.toLowerCase() === needle
		);

	const isAssigned = (tag: FolderTag) => assigned.some((item) => item.id === tag.id);

	async function mutate(action: () => Promise<FolderTag[]>, reset = false) {
		if (busy) return;
		busy = true;
		try {
			assigned = await action();
			if (reset) query = '';
			$userTags = await getAllTags(localStorage.token);
			await onChange();
		} catch (error) {
			toast.error(String(error));
		} finally {
			busy = false;
			input?.focus();
		}
	}

	const toggle = (tag: FolderTag) =>
		mutate(() =>
			isAssigned(tag)
				? deleteTagById(localStorage.token, chat.id, tag.name)
				: addTagById(localStorage.token, chat.id, tag.name)
		);

	async function opened(open: boolean) {
		if (!open) return;
		query = '';
		await tick();
		input?.focus();
		try {
			$userTags = await getAllTags(localStorage.token);
		} catch (error) {
			toast.error(String(error));
		}
	}
</script>

{#snippet pills()}
	{#each assigned.slice(0, max) as tag (tag.id)}
		<span
			class="inline-flex h-5 min-w-0 max-w-28 items-center gap-1.5 rounded-full border border-gray-100/60 pl-2 pr-1.25 text-[0.6875rem] text-gray-600 dark:border-gray-800/60 dark:text-gray-300"
			title={tag.name}
		>
			<span class="size-1.5 shrink-0 rounded-full {tagDot(tag)}"></span>
			<span class="truncate">{tag.name}</span>
		</span>
	{/each}
	{#if assigned.length > max}
		<span
			class="inline-flex h-5 shrink-0 items-center rounded-full border border-gray-100/60 px-1.5 text-[0.6875rem] text-gray-500 dark:border-gray-800/60 dark:text-gray-400"
			title={assigned
				.slice(max)
				.map((tag) => tag.name)
				.join(', ')}>+{assigned.length - max}</span
		>
	{/if}
{/snippet}

{#if chat.can_edit_tags}
	<Dropdown bind:show onOpenChange={opened} align="end">
		<button
			type="button"
			class="flex min-w-0 items-center gap-1 rounded-full"
			aria-label={$i18n.t('Edit tags for {{title}}', { title: chat.title })}
			title={assigned.length ? undefined : $i18n.t('Add tags')}
		>
			{@render pills()}
			{#if !assigned.length}
				<span
					class="tag-add flex h-5 items-center gap-1 rounded-full border border-dashed border-gray-200 px-1.5 text-[0.6875rem] text-gray-400 transition-colors hover:border-gray-300 hover:text-gray-600 dark:border-gray-700 dark:text-gray-500 dark:hover:text-gray-300"
					class:open={show}
				>
					<Plus className="size-2.5" strokeWidth="2" />{$i18n.t('Tag')}
				</span>
			{/if}
		</button>

		<DropdownMenu slot="content" className="w-52 text-gray-700 dark:text-gray-200">
			<form
				on:submit|preventDefault={() => {
					const exact = options.find((tag) => tag.name.toLowerCase() === needle);
					if (exact) void toggle(exact);
					else if (canCreate)
						void mutate(() => addTagById(localStorage.token, chat.id, query.trim()), true);
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
								class="flex size-3 shrink-0 items-center justify-center rounded-[0.25rem] border transition-colors {checked
									? 'border-gray-800 bg-gray-800 text-white dark:border-gray-100 dark:bg-gray-100 dark:text-gray-900'
									: 'border-gray-300 dark:border-gray-600'}"
							>
								{#if checked}<Check className="size-2" strokeWidth="3.5" />{/if}
							</span>
							<span class="size-1.5 shrink-0 rounded-full {tagDot(tag)}"></span>
							<span class="min-w-0 flex-1 truncate text-left">{tag.name}</span>
						</button>
						{#if checked}
							<Dropdown align="end" closeOnSelect>
								<button
									type="button"
									class="flex size-5 items-center justify-center rounded-md opacity-0 transition hover:bg-gray-100 focus-visible:opacity-100 group-hover/tag:opacity-100 dark:hover:bg-gray-800"
									aria-label={$i18n.t('Color for {{tag}}', { tag: tag.name })}
									title={$i18n.t('Applies wherever you use this tag')}
									disabled={busy}
								>
									<span
										class="size-2 rounded-full ring-2 ring-white dark:ring-gray-850 {tagDot(tag)}"
									></span>
								</button>
								<div
									slot="content"
									class="z-50 grid grid-cols-4 gap-0.5 rounded-xl border border-gray-100 bg-white p-1 shadow-lg dark:border-gray-800 dark:bg-gray-850"
								>
									{#each tagColors as color}
										<button
											type="button"
											role="menuitemradio"
											aria-checked={tagColor(tag) === color}
											aria-label={$i18n.t(color)}
											title={$i18n.t(color)}
											class="flex size-5 items-center justify-center rounded-md hover:bg-gray-50 dark:hover:bg-gray-800"
											disabled={busy}
											on:click={() =>
												mutate(() =>
													updateTagColorById(localStorage.token, chat.id, tag.name, color)
												)}
										>
											<span
												class="size-2.5 rounded-full {colorDot(color)} {tagColor(tag) === color
													? 'ring-2 ring-gray-300 ring-offset-1 ring-offset-white dark:ring-gray-600 dark:ring-offset-gray-850'
													: ''}"
											></span>
										</button>
									{/each}
								</div>
							</Dropdown>
						{/if}
					</div>
				{/each}

				{#if canCreate}
					<button
						type="button"
						class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-left text-[0.8125rem] hover:bg-gray-50/60 dark:hover:bg-gray-800/60"
						disabled={busy}
						on:click={() =>
							mutate(() => addTagById(localStorage.token, chat.id, query.trim()), true)}
					>
						<Plus className="size-3 text-gray-400" />
						<span class="min-w-0 truncate"
							>{$i18n.t('Create “{{name}}”', { name: query.trim() })}</span
						>
					</button>
				{:else if !options.length}
					<div class="px-2 py-1.5 text-xs text-gray-400 dark:text-gray-500">
						{$i18n.t('No tags yet. Type to create one.')}
					</div>
				{/if}
			</div>
		</DropdownMenu>
	</Dropdown>
{:else if assigned.length}
	<div class="flex min-w-0 items-center gap-1">{@render pills()}</div>
{/if}

<style>
	@media (hover: hover) {
		.tag-add {
			opacity: 0;
		}
		.tag-add.open,
		:global([data-folder-item]:hover) .tag-add,
		:global([data-folder-item]:focus-within) .tag-add {
			opacity: 1;
		}
	}
</style>
