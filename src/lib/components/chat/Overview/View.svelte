<script lang="ts">
	import { onDestroy } from 'svelte';
	import { useSvelteFlow, useNodesInitialized, useStore } from '@xyflow/svelte';

	import { onMount, tick } from 'svelte';

	import { writable } from 'svelte/store';
	import { models, user, chatId } from '$lib/stores';

	import '@xyflow/svelte/dist/style.css';

	import CustomNode from './Node.svelte';
	import Flow from './Flow.svelte';

	const { width, height, viewport } = useStore();

	const { fitView, setViewport } = useSvelteFlow();
	const nodesInitialized = useNodesInitialized();

	export let history;
	export let onClose;
	export let onNodeClick;

	let selectedMessageId = null;
	let viewportPinned = false;
	let isInitialized = false;
	let viewportSaveTimeout;
	let unsubs = [];

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

	$: if (isInitialized) {
		try {
			localStorage.setItem('overviewPinned', String(viewportPinned));
		} catch (e) {
			console.warn('Failed to save pinned state to local storage', e);
		}
	}

	$: if (isInitialized && $viewport && $chatId) {
		clearTimeout(viewportSaveTimeout);
		const vp = $viewport;
		const id = $chatId;
		viewportSaveTimeout = setTimeout(() => {
			try {
				let viewports = JSON.parse(localStorage.getItem('overviewViewports') || '{}');

				// Delete and re-insert to maintain insertion order for LRU eviction
				if (id in viewports) {
					delete viewports[id];
				}

				viewports[id] = vp;

				const keys = Object.keys(viewports);
				if (keys.length > 50) {
					delete viewports[keys[0]];
				}

				localStorage.setItem('overviewViewports', JSON.stringify(viewports));
			} catch (e) {
				console.warn('Failed to save viewport to local storage', e);
			}
		}, 300);
	}

	const focusNode = async () => {
		if (isInitialized && !viewportPinned) {
			if (selectedMessageId === null) {
				await fitView({ nodes: [{ id: history.currentId }] });
			} else {
				await fitView({ nodes: [{ id: selectedMessageId }] });
			}
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
		try {
			localStorage.setItem('overviewLayoutDirection', direction);
		} catch (e) {
			console.warn('Failed to save layout direction to local storage', e);
		}
		drawFlow(layoutDirection);
	};

	onMount(() => {
		try {
			viewportPinned = localStorage.getItem('overviewPinned') === 'true';
			layoutDirection = localStorage.getItem('overviewLayoutDirection') || 'vertical';
		} catch (e) {
			viewportPinned = false;
			layoutDirection = 'vertical';
		}
		drawFlow(layoutDirection);

		unsubs.push(
			nodesInitialized.subscribe(async (initialized) => {
				if (initialized) {
					await tick();
					
					let restored = false;
					if ($chatId) {
						try {
							const viewports = JSON.parse(localStorage.getItem('overviewViewports') || '{}');
							const saved = viewports[$chatId];

							if (saved) {
								const { x, y, zoom } = saved;
								await setViewport({ x, y, zoom });
								restored = true;
							}
						} catch (e) {
							// Ignored
						}
					}

					if (!restored) {
						await fitView({ nodes: [{ id: history.currentId }] });
					}
					isInitialized = true;
				}
			})
		);

		unsubs.push(
			width.subscribe((value) => {
				if (isInitialized && value && !viewportPinned) {
					fitView({ nodes: [{ id: history.currentId }] });
				}
			})
		);

		unsubs.push(
			height.subscribe((value) => {
				if (isInitialized && value && !viewportPinned) {
					fitView({ nodes: [{ id: history.currentId }] });
				}
			})
		);
	});

	onDestroy(() => {
		unsubs.forEach((unsub) => unsub());
		clearTimeout(viewportSaveTimeout);
		nodes.set([]);
		edges.set([]);
	});
</script>

<div class="w-full h-full relative">
	{#if $nodes.length > 0}
		<Flow
			{nodes}
			{nodeTypes}
			{edges}
			{setLayoutDirection}
			bind:viewportPinned
			onNodeClick={(detail) => {
				onNodeClick?.(detail);
				selectedMessageId = detail.node.data.message.id;
				if (!viewportPinned) {
					fitView({ nodes: [{ id: selectedMessageId }] });
				}
			}}
		/>
	{/if}
</div>
