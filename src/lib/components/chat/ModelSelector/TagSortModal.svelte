<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import { settings } from '$lib/stores';
	import { updateUserSettings } from '$lib/apis/users';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let tags: string[] = [];

	let sortedTags: string[] = [];
	let draggedIndex: number | null = null;
	let dropTargetIndex: number | null = null;
	let dropPosition: 'before' | 'after' | null = null;

	$: if (show && tags.length > 0) {
		// 初始化排序列表，使用已保存的顺序
		const savedOrder = $settings?.tagOrder ?? [];
		sortedTags = [...tags].sort((a, b) => {
			const aIndex = savedOrder.indexOf(a);
			const bIndex = savedOrder.indexOf(b);
			if (aIndex === -1 && bIndex === -1) return a.localeCompare(b);
			if (aIndex === -1) return 1;
			if (bIndex === -1) return -1;
			return aIndex - bIndex;
		});
	}

	const handleDragStart = (e: DragEvent, index: number) => {
		draggedIndex = index;
		if (e.dataTransfer) {
			e.dataTransfer.effectAllowed = 'move';
			e.dataTransfer.setData('text/plain', index.toString());
		}
	};

	const handleDragOver = (e: DragEvent, index: number) => {
		e.preventDefault();
		if (draggedIndex === null || draggedIndex === index) {
			dropTargetIndex = null;
			dropPosition = null;
			return;
		}

		if (e.dataTransfer) {
			e.dataTransfer.dropEffect = 'move';
		}

		const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
		const midY = rect.top + rect.height / 2;

		dropTargetIndex = index;
		dropPosition = e.clientY < midY ? 'before' : 'after';
	};

	const handleDragLeave = () => {
		// 延迟清除，避免在元素之间移动时闪烁
	};

	const handleDrop = (e: DragEvent, index: number) => {
		e.preventDefault();
		if (draggedIndex === null || draggedIndex === index) {
			resetDragState();
			return;
		}

		const newTags = [...sortedTags];
		const [draggedItem] = newTags.splice(draggedIndex, 1);

		// 计算实际插入位置
		let insertIndex = index;
		if (dropPosition === 'after') {
			insertIndex = index + 1;
		}
		// 如果从前面拖到后面，需要调整索引
		if (draggedIndex < index) {
			insertIndex--;
		}

		newTags.splice(insertIndex, 0, draggedItem);
		sortedTags = newTags;

		resetDragState();
	};

	const handleDragEnd = () => {
		resetDragState();
	};

	const resetDragState = () => {
		draggedIndex = null;
		dropTargetIndex = null;
		dropPosition = null;
	};

	// 上移
	const moveUp = (index: number) => {
		if (index === 0) return;
		const newTags = [...sortedTags];
		[newTags[index - 1], newTags[index]] = [newTags[index], newTags[index - 1]];
		sortedTags = newTags;
	};

	// 下移
	const moveDown = (index: number) => {
		if (index === sortedTags.length - 1) return;
		const newTags = [...sortedTags];
		[newTags[index], newTags[index + 1]] = [newTags[index + 1], newTags[index]];
		sortedTags = newTags;
	};

	const saveOrder = async () => {
		settings.set({ ...$settings, tagOrder: sortedTags });
		await updateUserSettings(localStorage.token, { ui: $settings });
		toast.success($i18n.t('标签顺序已保存'));
		dispatch('save', { tagOrder: sortedTags });
		show = false;
	};

	const resetOrder = () => {
		sortedTags = [...tags].sort((a, b) => a.localeCompare(b));
	};
</script>

<Modal bind:show size="xs">
	<div class="px-5 py-4">
		<div class="flex justify-between items-center mb-4">
			<h3 class="text-lg font-medium">{$i18n.t('标签排序')}</h3>
			<button
				class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
				aria-label="关闭"
				on:click={() => (show = false)}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="2"
					stroke="currentColor"
					class="size-5"
				>
					<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
				</svg>
			</button>
		</div>

		<p class="text-sm text-gray-500 dark:text-gray-400 mb-3">
			{$i18n.t('拖拽或使用箭头调整标签顺序')}
		</p>

		<div class="flex flex-col max-h-64 overflow-y-auto">
			{#each sortedTags as tag, index (tag)}
				<!-- 顶部插入线 -->
				{#if dropTargetIndex === index && dropPosition === 'before' && draggedIndex !== index}
					<div class="h-0.5 bg-blue-500 rounded-full mx-2 my-0.5"></div>
				{/if}

				<div
					draggable="true"
					on:dragstart={(e) => handleDragStart(e, index)}
					on:dragover={(e) => handleDragOver(e, index)}
					on:dragleave={handleDragLeave}
					on:drop={(e) => handleDrop(e, index)}
					on:dragend={handleDragEnd}
					role="listitem"
					class="flex items-center gap-2 px-3 py-2 my-0.5 rounded-lg cursor-move transition-opacity
						{draggedIndex === index ? 'opacity-40' : 'opacity-100'}
						bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700"
				>
					<!-- 拖拽手柄 -->
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="1.5"
						stroke="currentColor"
						class="size-4 text-gray-400 shrink-0"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
						/>
					</svg>
					<span class="text-sm capitalize flex-1">{tag}</span>
					<!-- 上下移动按钮 -->
					<div class="flex gap-1 shrink-0">
						<button
							class="p-0.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 disabled:opacity-30 disabled:cursor-not-allowed"
							disabled={index === 0}
							aria-label="上移"
							on:click|stopPropagation={() => moveUp(index)}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="2"
								stroke="currentColor"
								class="size-4"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="M4.5 15.75l7.5-7.5 7.5 7.5" />
							</svg>
						</button>
						<button
							class="p-0.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 disabled:opacity-30 disabled:cursor-not-allowed"
							disabled={index === sortedTags.length - 1}
							aria-label="下移"
							on:click|stopPropagation={() => moveDown(index)}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="2"
								stroke="currentColor"
								class="size-4"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
							</svg>
						</button>
					</div>
				</div>

				<!-- 底部插入线（只在最后一个元素后面显示） -->
				{#if dropTargetIndex === index && dropPosition === 'after' && draggedIndex !== index}
					<div class="h-0.5 bg-blue-500 rounded-full mx-2 my-0.5"></div>
				{/if}
			{/each}
		</div>

		{#if sortedTags.length === 0}
			<div class="text-center text-gray-500 dark:text-gray-400 py-4">
				{$i18n.t('没有可排序的标签')}
			</div>
		{/if}

		<div class="flex justify-between mt-4 pt-3 border-t dark:border-gray-700">
			<button
				class="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
				on:click={resetOrder}
			>
				{$i18n.t('重置')}
			</button>
			<button
				class="px-4 py-1.5 text-sm bg-black dark:bg-white text-white dark:text-black rounded-lg hover:opacity-80 transition"
				on:click={saveOrder}
			>
				{$i18n.t('保存')}
			</button>
		</div>
	</div>
</Modal>
