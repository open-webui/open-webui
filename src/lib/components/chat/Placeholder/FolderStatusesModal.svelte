<script lang="ts">
	import { getContext, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { newStatusId, statusGlyphs, type CustomStatus, type StatusDef } from '$lib/utils/folders';
	import { colorDot, tagColors } from '$lib/utils/tags';
	import Modal from '$lib/components/common/Modal.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import EmojiPicker from '$lib/components/common/EmojiPicker.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import StatusIcon from './FolderStatusIcon.svelte';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');

	export let show = false;
	export let statuses: StatusDef[] = [];
	export let onSave: (statuses: CustomStatus[]) => Promise<void>;

	let draft: CustomStatus[] = [];
	let saving = false;
	let list: HTMLDivElement;
	let wasOpen = false;
	let dragId = '';

	const glyphLabels: Record<string, string> = {
		backlog: 'Dashed',
		todo: 'Ring',
		in_progress: 'Half',
		waiting: 'Three quarters',
		done: 'Done'
	};

	// Start a fresh draft each time the modal opens.
	$: {
		if (show && !wasOpen)
			draft = statuses
				.filter((item) => item.custom)
				.map(({ id, name, glyph, color, icon }) => ({ id, name, glyph, color, icon }));
		wasOpen = show;
	}

	const update = (id: string, patch: Partial<CustomStatus>) =>
		(draft = draft.map((item) => (item.id === id ? { ...item, ...patch } : item)));

	async function add() {
		draft = [...draft, { id: newStatusId(), name: '', glyph: 'todo', color: 'gray' }];
		await tick();
		[...(list?.querySelectorAll<HTMLInputElement>('input[data-status-name]') ?? [])]
			.at(-1)
			?.focus();
	}

	function reorder(overId: string) {
		if (!dragId || dragId === overId) return;
		const from = draft.findIndex((item) => item.id === dragId);
		const to = draft.findIndex((item) => item.id === overId);
		if (from < 0 || to < 0) return;
		const next = [...draft];
		next.splice(to, 0, ...next.splice(from, 1));
		draft = next;
	}

	async function save() {
		const cleaned = draft
			.map((item) => ({ ...item, name: item.name.trim() }))
			.filter((item) => item.name);
		const names = cleaned.map((item) => item.name.toLowerCase());
		if (
			new Set(names).size !== names.length ||
			names.includes($i18n.t('No status').toLowerCase())
		) {
			toast.error($i18n.t('Status names must be unique.'));
			return;
		}
		saving = true;
		try {
			await onSave(cleaned);
			show = false;
		} catch (error) {
			toast.error(String(error));
		} finally {
			saving = false;
		}
	}
</script>

<Modal size="sm" bind:show ariaLabel={$i18n.t('Statuses')}>
	<div class="px-4 pt-3 pb-4 dark:text-gray-200">
		<div class="flex items-center justify-between pb-2 dark:text-gray-300">
			<div class="text-sm">{$i18n.t('Statuses')}</div>
			<button
				aria-label={$i18n.t('Close')}
				class="rounded-lg py-1 text-gray-500 transition hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
				on:click={() => (show = false)}><XMark className="size-4" /></button
			>
		</div>

		<form on:submit|preventDefault={save}>
			<div bind:this={list} class="max-h-[60vh] overflow-y-auto">
				<div class="flex h-8 items-center gap-2 px-1 text-sm text-gray-500 dark:text-gray-400">
					<span class="w-3 shrink-0"></span>
					<span class="flex size-6 items-center justify-center"><StatusIcon /></span>
					<span class="flex-1">{$i18n.t('No status')}</span>
					<span class="text-xs text-gray-400 dark:text-gray-500">{$i18n.t('Default')}</span>
				</div>

				{#each draft as item (item.id)}
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<div
						class="group flex h-8 items-center gap-2 rounded-lg px-1 transition-opacity {dragId ===
						item.id
							? 'opacity-40'
							: ''}"
						draggable={dragId === item.id}
						on:dragstart={(event) => {
							if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move';
						}}
						on:dragover|preventDefault={() => reorder(item.id)}
						on:dragend={() => (dragId = '')}
					>
						<span
							class="flex w-3 shrink-0 cursor-grab justify-center text-gray-300 opacity-0 transition group-hover:opacity-100 dark:text-gray-600"
							role="button"
							tabindex="-1"
							aria-label={$i18n.t('Reorder')}
							on:pointerdown={() => (dragId = item.id)}
							on:pointerup={() => (dragId = '')}
						>
							<svg class="size-3" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true"
								><circle cx="4" cy="3" r="1" /><circle cx="8" cy="3" r="1" /><circle
									cx="4"
									cy="6"
									r="1"
								/><circle cx="8" cy="6" r="1" /><circle cx="4" cy="9" r="1" /><circle
									cx="8"
									cy="9"
									r="1"
								/></svg
							>
						</span>

						<Dropdown align="start">
							<button
								type="button"
								class="flex size-6 shrink-0 items-center justify-center rounded-lg transition hover:bg-gray-50 dark:hover:bg-gray-850"
								aria-label={$i18n.t('Change status icon')}
								title={$i18n.t('Change status icon')}
							>
								<StatusIcon glyph={item.glyph} color={item.color} emoji={item.icon} />
							</button>
							<DropdownMenu slot="content" className="w-48">
								<div class="px-2 pt-1.5 pb-0.5 text-xs text-gray-400 dark:text-gray-500">
									{$i18n.t('Icon')}
								</div>
								<div class="flex gap-0.5 px-1 pb-1">
									{#each statusGlyphs as glyph}
										<button
											type="button"
											role="menuitemradio"
											aria-checked={!item.icon && item.glyph === glyph}
											aria-label={$i18n.t(glyphLabels[glyph])}
											title={$i18n.t(glyphLabels[glyph])}
											class="flex size-7 items-center justify-center rounded-lg transition hover:bg-gray-50 dark:hover:bg-gray-800 {!item.icon &&
											item.glyph === glyph
												? 'bg-gray-50 dark:bg-gray-800'
												: ''}"
											on:click={() => update(item.id, { glyph, icon: undefined })}
										>
											<StatusIcon {glyph} color={item.color} />
										</button>
									{/each}
								</div>
								<div class="px-2 pt-0.5 pb-0.5 text-xs text-gray-400 dark:text-gray-500">
									{$i18n.t('Color')}
								</div>
								<div class="grid grid-cols-8 gap-0.5 px-1 pb-1">
									{#each tagColors as color}
										<button
											type="button"
											role="menuitemradio"
											aria-checked={item.color === color}
											aria-label={$i18n.t(color)}
											title={$i18n.t(color)}
											class="flex size-5 items-center justify-center rounded-md hover:bg-gray-50 dark:hover:bg-gray-800"
											on:click={() => update(item.id, { color, icon: undefined })}
										>
											<span
												class="size-2.5 rounded-full {colorDot(color)} {item.color === color &&
												!item.icon
													? 'ring-2 ring-gray-300 ring-offset-1 ring-offset-white dark:ring-gray-600 dark:ring-offset-gray-850'
													: ''}"
											></span>
										</button>
									{/each}
								</div>
								<hr class="border-gray-50/30 dark:border-gray-800/30" />
								<EmojiPicker
									side="bottom"
									selected={item.icon ?? null}
									onSubmit={(icon: string | null) => update(item.id, { icon: icon ?? undefined })}
								>
									<button
										type="button"
										class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[0.8125rem] hover:bg-gray-50/60 dark:hover:bg-gray-800/60"
									>
										<span class="flex-1 text-left">{$i18n.t('Use emoji…')}</span>
										{#if item.icon}<Check className="size-3! shrink-0" />{/if}
									</button>
								</EmojiPicker>
							</DropdownMenu>
						</Dropdown>

						<input
							data-status-name
							class="min-w-0 flex-1 bg-transparent text-sm outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700"
							placeholder={$i18n.t('Status name')}
							maxlength="40"
							value={item.name}
							on:input={(event) => update(item.id, { name: event.currentTarget.value })}
						/>
						<button
							type="button"
							class="rounded-lg p-1 text-gray-400 opacity-0 transition group-hover:opacity-100 group-focus-within:opacity-100 hover:text-gray-700 dark:hover:text-gray-200"
							aria-label={$i18n.t('Delete status')}
							on:click={() => (draft = draft.filter((entry) => entry.id !== item.id))}
							><XMark className="size-3.5" /></button
						>
					</div>
				{/each}

				<button
					type="button"
					class="flex h-8 w-full items-center gap-2 rounded-lg px-1 text-sm text-gray-500 transition hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200"
					on:click={add}
				>
					<span class="w-3 shrink-0"></span>
					<span class="flex size-6 items-center justify-center"><Plus className="size-3.5" /></span>
					{$i18n.t('Add status')}
				</button>
			</div>

			<p class="mt-2 text-xs text-gray-400 dark:text-gray-500">
				{$i18n.t('Chats in a deleted status go back to “No status”.')}
			</p>

			<div class="mt-3 flex justify-end">
				<button
					class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-gray-900 px-2.5 text-xs font-normal text-white transition hover:bg-black disabled:cursor-not-allowed disabled:opacity-60 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white"
					type="submit"
					disabled={saving}
				>
					{$i18n.t('Save')}
					{#if saving}<Spinner className="size-3" />{/if}
				</button>
			</div>
		</form>
	</div>
</Modal>
