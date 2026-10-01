<script lang="ts">
	import { onMount, tick } from 'svelte';
	import {
		useSvelteFlow,
		useNodesInitialized,
		useStore,
		type Edge,
		type Node
	} from '@xyflow/svelte';

	import { writable } from 'svelte/store';
	import { models, user } from '$lib/stores';

	import '@xyflow/svelte/dist/style.css';

	import CustomNode from './Node.svelte';
	import Flow from './Flow.svelte';

	const { width, height } = useStore();

	const { fitView } = useSvelteFlow();
	const nodesInitialized = useNodesInitialized();

	export let history;
	export let onNodeClick;
	export let chatUser = null;

	type LayoutDirection = 'vertical' | 'horizontal';
	type PositionMapEntry = {
		id: string;
		level: number;
		position: number;
	};

	let selectedMessageId: string | null = null;
	let pinned = false;

	const nodes = writable<Node[]>([]);
	const edges = writable<Edge[]>([]);

	let layoutDirection: LayoutDirection = 'vertical';

	const nodeTypes = {
		custom: CustomNode
	};

	$: if (history) {
		drawFlow(layoutDirection);
	}

	$: if (history && history.currentId && !pinned) {
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

	const drawFlow = async (direction: LayoutDirection) => {
		const nodeList: Node[] = [];
		const edgeList: Edge[] = [];
		const rootFontSize = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
		const nodeWidth = 15 * rootFontSize;
		const nodeHeight = 5 * rootFontSize;
		const levelOffset = direction === 'vertical' ? nodeHeight + 70 : nodeWidth + 60;
		const siblingOffset = direction === 'vertical' ? nodeWidth + 60 : nodeHeight + 70;

		// Map to keep track of node positions at each level
		let positionMap = new Map<string, PositionMapEntry>();

		// Create nodes and map children to ensure alignment in width
		let layerWidths: Record<number, number> = {}; // Track widths of each layer

		Object.keys(history.messages).forEach((id) => {
			const message = history.messages[id];
			if (!message) return;

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
			if (!pos) return;

			const x = direction === 'vertical' ? pos.position * siblingOffset : pos.level * levelOffset;
			const y = direction === 'vertical' ? pos.level * levelOffset : pos.position * siblingOffset;

			nodeList.push({
				id: pos.id,
				type: 'custom',
				data: {
					user: chatUser ?? $user,
					message: history.messages[id],
					model: $models.find((model) => model.id === history.messages[id].model),
					direction
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

	const recurseCheckChild = (nodeId: string, currentId: string): boolean => {
		const node = history.messages[nodeId];
		return (
			node.childrenIds &&
			node.childrenIds.some((id: string) => id === currentId || recurseCheckChild(id, currentId))
		);
	};

	const setLayoutDirection = (direction: LayoutDirection) => {
		layoutDirection = direction;
		drawFlow(layoutDirection);
	};

	onMount(() => {
		drawFlow(layoutDirection);

		const stopNodesInitialized = nodesInitialized.subscribe(async (initialized) => {
			if (initialized && !pinned) {
				await tick();
				await fitView({ nodes: [{ id: history.currentId }] });
			}
		});
		const stopWidth = width.subscribe((value) => {
			if (value && !pinned) {
				fitView({ nodes: [{ id: history.currentId }] });
			}
		});
		const stopHeight = height.subscribe((value) => {
			if (value && !pinned) {
				fitView({ nodes: [{ id: history.currentId }] });
			}
		});

		return () => {
			console.log('Overview destroyed');
			stopNodesInitialized();
			stopWidth();
			stopHeight();
			nodes.set([]);
			edges.set([]);
		};
	});
</script>

<div class="w-full h-full relative">
	{#if $nodes.length > 0}
		<Flow
			{nodes}
			{nodeTypes}
			{edges}
			{setLayoutDirection}
			bind:pinned
			on:nodeclick={(e) => {
				onNodeClick(e.detail);
				const clickedMessageId = e.detail.node.data.message.id as string;
				selectedMessageId = clickedMessageId;
				if (!pinned) {
					fitView({ nodes: [{ id: clickedMessageId }] });
				}
			}}
		/>
	{/if}
</div>
