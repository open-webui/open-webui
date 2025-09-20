<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { goto } from '$app/navigation';
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import ArrowDownTray from '../../icons/ArrowDownTray.svelte';
	import Pencil from '../../icons/Pencil.svelte';
	import GarbageBin from '../../icons/GarbageBin.svelte';
	import Heart from '../../icons/Heart.svelte';
	import ChevronRight from '../../icons/ChevronRight.svelte';

	const i18n = getContext('i18n');

	export let workflow: any;
	export let onShare: (workflow: any) => void;
	export let onClone: (workflow: any) => void;
	export let onExport: (workflow: any) => void;
	export let onDelete: (workflow: any) => void;

	const dispatch = createEventDispatcher();

	let show = false;

	const handleShare = () => {
		onShare(workflow);
		show = false;
	};

	const handleClone = () => {
		onClone(workflow);
		show = false;
	};

	const handleExport = () => {
		onExport(workflow);
		show = false;
	};

	const handleDelete = () => {
		onDelete(workflow);
		show = false;
	};

	const handleEdit = () => {
		goto(`/workspace/workflows/edit?id=${workflow.id}`);
		show = false;
	};
</script>

<div class="relative">
	<button
		class="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 transition"
		on:click={() => (show = !show)}
		on:blur={() => setTimeout(() => (show = false), 150)}
	>
		<slot />
	</button>

	{#if show}
		<div
			class="absolute right-0 top-full mt-1 w-48 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-50"
			on:click|stopPropagation
			role="menu"
			tabindex="-1"
		>
			<div class="py-1">
				<button
					class="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition"
					on:click={handleEdit}
				>
					<Pencil className="size-4" />
					{$i18n.t('Edit')}
				</button>

				<button
					class="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition"
					on:click={handleClone}
				>
					<ChevronRight className="size-4" />
					{$i18n.t('Clone')}
				</button>

				<button
					class="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition"
					on:click={handleExport}
				>
					<ArrowDownTray className="size-4" />
					{$i18n.t('Export')}
				</button>

				<button
					class="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition"
					on:click={handleShare}
				>
					<Heart className="size-4" />
					{$i18n.t('Share')}
				</button>

				<div class="border-t border-gray-200 dark:border-gray-700 my-1"></div>

				<button
					class="flex items-center gap-2 w-full px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition"
					on:click={handleDelete}
				>
					<GarbageBin className="size-4" />
					{$i18n.t('Delete')}
				</button>
			</div>
		</div>
	{/if}
</div>
