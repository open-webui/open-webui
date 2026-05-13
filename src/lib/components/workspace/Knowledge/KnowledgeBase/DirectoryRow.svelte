<script lang="ts">
	import dayjs from '$lib/dayjs';
	import duration from 'dayjs/plugin/duration';
	import relativeTime from 'dayjs/plugin/relativeTime';

	dayjs.extend(duration);
	dayjs.extend(relativeTime);

	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import Folder from '$lib/components/icons/Folder.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';

	export let directory: {
		id: string;
		name: string;
		created_at: number;
		updated_at: number;
	};
	export let writeAccess = false;

	export let onNavigate: (id: string) => void = () => {};
	export let onRename: (id: string, name: string) => void = () => {};
	export let onDelete: (id: string) => void = () => {};
	export let onFileDrop: (fileId: string, directoryId: string) => void = () => {};
	export let onDirDrop: (dirId: string, targetDirectoryId: string) => void = () => {};
	let editing = false;
	let editName = '';
	let editInput: HTMLInputElement;
	let dragOver = false;
	let showDropdown = false;

	const startRename = () => {
		editName = directory.name;
		editing = true;
		showDropdown = false;
		setTimeout(() => editInput?.select(), 0);
	};

	const submitRename = () => {
		if (!editName.trim() || editName === directory.name) {
			editing = false;
			return;
		}
		onRename(directory.id, editName.trim());
		editing = false;
	};

	const cancelRename = () => {
		editing = false;
	};
</script>

<!-- svelte-ignore a11y-no-static-element-interactions -->
<div
	class="group flex cursor-pointer w-full px-2 bg-transparent dark:hover:bg-gray-850/50 hover:bg-white rounded-xl transition
		{dragOver
		? 'bg-gray-100 dark:bg-gray-800 ring-1 ring-gray-300 dark:ring-gray-600'
		: 'hover:bg-gray-100 dark:hover:bg-gray-850'}"
	draggable="true"
	on:dragstart={(e) => {
		e.dataTransfer?.setData(
			'application/x-kb-dir-move',
			JSON.stringify({ dirId: directory.id })
		);
	}}
	on:dblclick={() => {
		if (writeAccess) startRename();
	}}
	on:dragover={(e) => {
		const hasFile = e.dataTransfer?.types.includes('application/x-kb-file-move');
		const hasDir = e.dataTransfer?.types.includes('application/x-kb-dir-move');
		if (!hasFile && !hasDir) return;
		e.preventDefault();
		e.stopPropagation();
		dragOver = true;
	}}
	on:dragleave={() => {
		dragOver = false;
	}}
	on:drop={(e) => {
		e.preventDefault();
		e.stopPropagation();
		dragOver = false;
		const fileRaw = e.dataTransfer?.getData('application/x-kb-file-move');
		if (fileRaw) {
			try {
				const data = JSON.parse(fileRaw);
				onFileDrop(data.fileId, directory.id);
			} catch {}
			return;
		}
		const dirRaw = e.dataTransfer?.getData('application/x-kb-dir-move');
		if (dirRaw) {
			try {
				const data = JSON.parse(dirRaw);
				if (data.dirId !== directory.id) {
					onDirDrop(data.dirId, directory.id);
				}
			} catch {}
		}
	}}
>
	<div class="flex items-center">
		<button
			class="p-1 rounded-full transition"
			type="button"
			on:click={() => onNavigate(directory.id)}
		>
			<Folder className="size-3.5" />
		</button>
	</div>

	<button
		class="relative flex items-center gap-1 rounded-xl p-2 text-left flex-1 justify-between"
		type="button"
		on:click={() => onNavigate(directory.id)}
	>
		<div>
			<div class="flex gap-2 items-center line-clamp-1">
				{#if editing}
					<!-- svelte-ignore a11y-autofocus -->
					<input
						bind:this={editInput}
						bind:value={editName}
						class="text-sm w-full bg-transparent border-none outline-hidden"
						on:keydown={(e) => {
							if (e.key === 'Enter') submitRename();
							if (e.key === 'Escape') cancelRename();
						}}
						on:blur={submitRename}
						on:click={(e) => e.stopPropagation()}
						autofocus
					/>
				{:else}
					<div class="line-clamp-1 text-sm">
						{directory.name}
					</div>
				{/if}
			</div>
		</div>

		<div class="flex items-center gap-2 shrink-0">
			{#if directory.updated_at}
				<Tooltip content={dayjs(directory.updated_at * 1000).format('LLLL')}>
					<div class="text-xs text-gray-400">
						{dayjs(directory.updated_at * 1000).fromNow()}
					</div>
				</Tooltip>
			{/if}
		</div>
	</button>

	{#if writeAccess}
		<div class="flex items-center">
			<Dropdown bind:show={showDropdown} align="end" sideOffset={4}>
				<button
					class="p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-850 transition"
					type="button"
				>
					<EllipsisHorizontal className="size-3.5" />
				</button>

				<div slot="content">
					<div
						class="min-w-[140px] rounded-2xl p-1 z-[9999999] bg-white dark:bg-gray-850 dark:text-white shadow-lg border border-gray-100 dark:border-gray-800"
					>
						<button
							type="button"
							class="select-none flex rounded-xl py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition items-center gap-2 text-sm"
							on:click={() => startRename()}
						>
							<Pencil className="size-3.5" />
							{$i18n.t('Rename')}
						</button>
						<button
							type="button"
							class="select-none flex rounded-xl py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition items-center gap-2 text-sm"
							on:click={() => onDelete(directory.id)}
						>
							<GarbageBin className="size-3.5" />
							{$i18n.t('Delete')}
						</button>
					</div>
				</div>
			</Dropdown>
		</div>
	{/if}
</div>
