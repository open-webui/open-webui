<script lang="ts">
	import { getContext, createEventDispatcher, onDestroy } from 'svelte';
	import { useSvelteFlow, useNodesInitialized, useStore } from '@xyflow/svelte';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import { onMount, tick } from 'svelte';

	import { writable } from 'svelte/store';
	import { models, theme, user } from '$lib/stores';

	import '@xyflow/svelte/dist/style.css';

	import CustomNode from './Node.svelte';
	import AgentNode from './AgentNode.svelte';
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
	let viewMode: 'chat' | 'execution' = 'execution';

	// Store the graph data extracted from messages
	let executionGraph: { nodes: any[]; edges: any[] } | null = null;

	const nodeTypes = {
		custom: CustomNode,
		agent: AgentNode
	};

	$: if (history) {
		if (viewMode === 'execution') {
			drawExecutionFlow(layoutDirection);
		} else {
			drawFlow(layoutDirection);
		}
	}

	$: if (history && history.currentId) {
		focusNode();
	}

	// Extract execution-graph from any message output
	const extractExecutionGraph = (): { nodes: any[]; edges: any[] } | null => {
		if (!history?.messages) return null;
		for (const id of Object.keys(history.messages)) {
			const msg = history.messages[id];
			let text: string = '';
			// Try direct string properties first
			if (typeof msg?.output === 'string') text = msg.output;
			else if (typeof msg?.content === 'string' && msg.content.length > 0) text = msg.content;
			else if (Array.isArray(msg?.content)) {
				text = msg.content.map((c: any) => (typeof c === 'string' ? c : c?.text || '')).join('\n');
			}
			// OWUI stores assistant messages in output as an array of message objects
			if (!text && Array.isArray(msg?.output)) {
				for (const part of msg.output) {
					if (part?.content) {
						const parts = Array.isArray(part.content) ? part.content : [part.content];
						for (const c of parts) {
							if (c?.text) text += c.text;
							else if (typeof c === 'string') text += c;
						}
					}
				}
			}
			if (!text && typeof msg?.output === 'object' && msg.output) {
				text = msg.output.text || msg.output.content || msg.output.markdown || '';
				if (typeof text !== 'string') text = JSON.stringify(text);
			}
			if (!text) continue;
			const match = text.match(/```execution-graph\s*\n([\s\S]*?)```/);
			if (match) {
				try {
					const parsed = JSON.parse(match[1]);
					if (parsed.nodes && parsed.edges) return parsed;
				} catch (e) { /* ignore parse errors */ }
			}
		}
		return null;
	};

	// Build the execution flow from graph JSON
	const drawExecutionFlow = async (direction: string) => {
		const graph = extractExecutionGraph();
		if (!graph) {
			executionGraph = null;
			// Don't flip viewMode — stay in 'execution' so history updates re-trigger extraction
			drawFlow(direction);
			return;
		}
		executionGraph = graph;

		const nodeList: any[] = [];
		const edgeList: any[] = [];
		const spacingX = direction === 'vertical' ? 220 : 350;
		const spacingY = direction === 'vertical' ? 180 : 180;

		// Simple layered layout: group by nodeType
		const layerOrder = ['router', 'agent', 'critique', 'synthesis', 'output'];
		const layerMap = new Map<string, number>();
		const layerCounts = new Map<number, number>();

		graph.nodes.forEach((n: any) => {
			const layer = layerOrder.indexOf(n.nodeType ?? 'agent');
			const effectiveLayer = layer >= 0 ? layer : 2;
			layerMap.set(n.id, effectiveLayer);
			layerCounts.set(effectiveLayer, (layerCounts.get(effectiveLayer) ?? 0) + 1);
		});

		// Track position within each layer
		const layerPos = new Map<number, number>();
		layerCounts.forEach((_, k) => layerPos.set(k, 0));

		graph.nodes.forEach((n: any, i: number) => {
			const layer = layerMap.get(n.id) ?? 2;
			const pos = layerPos.get(layer) ?? 0;
			const x = direction === 'vertical' ? pos * spacingX : layer * spacingY;
			const y = direction === 'vertical' ? layer * spacingY : pos * spacingX;

			nodeList.push({
				id: n.id,
				type: 'agent',
				data: {
					label: n.label,
					nodeType: n.nodeType ?? 'agent',
					tools: n.tools ?? [],
					status: n.status ?? 'done',
					round: n.round ?? 1
				},
				position: { x, y }
			});

			layerPos.set(layer, pos + 1);
		});

		graph.edges.forEach((e: any) => {
			edgeList.push({
				id: `${e.source}-${e.target}`,
				source: e.source,
				target: e.target,
				selectable: false,
				class: 'dark:fill-gray-400 fill-gray-400',
				type: 'smoothstep',
				animated: e.animated ?? true
			});
		});

		await edges.set([...edgeList]);
		await nodes.set([...nodeList]);
	};

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
	<!-- Toggle: Chat / Execution -->
	{#if executionGraph || extractExecutionGraph()}
		<div class="absolute top-2 left-2 z-10 flex gap-1">
			<button
				class="px-2 py-1 text-xs rounded-md {viewMode === 'chat' ? 'bg-gray-200 dark:bg-gray-700 font-medium' : 'bg-transparent hover:bg-gray-100 dark:hover:bg-gray-800'}"
				on:click={() => { viewMode = 'chat'; drawFlow(layoutDirection); }}
			>
				💬 Chat
			</button>
			<button
				class="px-2 py-1 text-xs rounded-md {viewMode === 'execution' ? 'bg-gray-200 dark:bg-gray-700 font-medium' : 'bg-transparent hover:bg-gray-100 dark:hover:bg-gray-800'}"
				on:click={() => { viewMode = 'execution'; drawExecutionFlow(layoutDirection); }}
			>
				🧪 Execution
			</button>
		</div>
	{/if}
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
