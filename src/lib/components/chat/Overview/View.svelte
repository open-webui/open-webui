<script lang="ts">
	import { getContext, createEventDispatcher, onDestroy } from 'svelte';
	import { useSvelteFlow, useNodesInitialized, useStore } from '@xyflow/svelte';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import { onMount, tick } from 'svelte';

	import { writable } from 'svelte/store';
	import { models, showOverview, theme, user } from '$lib/stores';

	import '@xyflow/svelte/dist/style.css';

	import CustomNode from './Node.svelte';
	import Flow from './Flow.svelte';
	import XMark from '../../icons/XMark.svelte';
	import ArrowLeft from '../../icons/ArrowLeft.svelte';

	const { width, height } = useStore();

	const { fitView, getViewport } = useSvelteFlow();
	const nodesInitialized = useNodesInitialized();

	export let history;
	export let onClose;
	export let onNodeClick;

	let selectedMessageId = null;

	const nodes = writable([]);
	const edges = writable([]);

	let layoutDirection = 'vertical';

	const nodeTypes = {
		custom: CustomNode
	};

	$: if (history) {
		drawFlow(layoutDirection);
	}

	$: if (history && history.currentId) {
		focusNode();
	}

	const focusNode = async () => {
		if (selectedMessageId === null) {
			await fitView({ nodes: [{ id: history.currentId }] });
		} else {
			await fitView({ nodes: [{ id: selectedMessageId }] });
		}

		selectedMessageId = null;
	};

	const drawFlow = async (direction) => {
		const nodeList = [];
		const edgeList = [];
		const levelOffset = direction === 'vertical' ? 150 : 300;
		const siblingOffset = direction === 'vertical' ? 250 : 150;

		// Map to keep track of node positions at each level
		let positionMap = new Map();

		// Helper function to truncate labels
		function createLabel(content) {
			const maxLength = 100;
			return content.length > maxLength ? content.substr(0, maxLength) + '...' : content;
		}

		// Create nodes and map children to ensure alignment in width
		let layerWidths = {}; // Track widths of each layer

		Object.keys(history.messages).forEach((id) => {
			const message = history.messages[id];
			const level = message.parentId ? (positionMap.get(message.parentId)?.level ?? -1) + 1 : 0;
			if (!layerWidths[level]) layerWidths[level] = 0;

			positionMap.set(id, {
				id: message.id,
				level,
				position: layerWidths[level]++
			});
		});

		// Adjust positions based on siblings count to centralize vertical spacing
		Object.keys(history.messages).forEach((id) => {
			const pos = positionMap.get(id);
			const x = direction === 'vertical' ? pos.position * siblingOffset : pos.level * levelOffset;
			const y = direction === 'vertical' ? pos.level * levelOffset : pos.position * siblingOffset;

			nodeList.push({
				id: pos.id,
				type: 'custom',
				data: {
					user: $user,
					message: history.messages[id],
					model: $models.find((model) => model.id === history.messages[id].model)
				},
				position: { x, y }
			});

			// Create edges
			const parentId = history.messages[id].parentId;
			if (parentId) {
				edgeList.push({
					id: parentId + '-' + pos.id,
					source: parentId,
					target: pos.id,
					selectable: false,
					class: ' dark:fill-gray-300 fill-gray-300',
					type: 'smoothstep',
					animated: history.currentId === id || recurseCheckChild(id, history.currentId)
				});
			}
		});

		await edges.set([...edgeList]);
		await nodes.set([...nodeList]);
	};

	const recurseCheckChild = (nodeId, currentId) => {
		const node = history.messages[nodeId];
		return (
			node.childrenIds &&
			node.childrenIds.some((id) => id === currentId || recurseCheckChild(id, currentId))
		);
	};

	const setLayoutDirection = (direction) => {
		layoutDirection = direction;
		drawFlow(layoutDirection);
	};

	onMount(() => {
		drawFlow(layoutDirection);

		nodesInitialized.subscribe(async (initialized) => {
			if (initialized) {
				await tick();
				const res = await fitView({ nodes: [{ id: history.currentId }] });
			}
		});

		width.subscribe((value) => {
			if (value) {
				// fitView();
				fitView({ nodes: [{ id: history.currentId }] });
			}
		});

		height.subscribe((value) => {
			if (value) {
				// fitView();
				fitView({ nodes: [{ id: history.currentId }] });
			}
		});
	});

	onDestroy(() => {
		console.log('Overview destroyed');

		nodes.set([]);
		edges.set([]);
	});
</script>

<div class="w-full h-full relative">
	<div class=" absolute z-50 w-full flex justify-between dark:text-gray-100 px-4 py-3">
		<div class="flex items-center gap-2.5">
			<button
				class="self-center p-0.5"
				on:click={() => {
					showOverview.set(false);
				}}
			>
				<ArrowLeft className="size-3.5" />
			</button>
			<div class=" text-lg font-medium self-center font-primary">{$i18n.t('Chat Overview')}</div>
		</div>
		<button
			class="self-center p-0.5"
			on:click={() => {
				onClose();
				showOverview.set(false);
			}}
		>
			<XMark className="size-3.5" />
		</button>
	</div>

	{#if $nodes.length > 0}
		<Flow
			{nodes}
			{nodeTypes}
			{edges}
			{setLayoutDirection}
			on:nodeclick={(e) => {
				onNodeClick(e.detail);
				selectedMessageId = e.detail.node.data.message.id;
				fitView({ nodes: [{ id: selectedMessageId }] });
			}}
		/>
	{/if}
</div>
