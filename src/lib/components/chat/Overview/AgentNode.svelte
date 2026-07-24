<script lang="ts">
	import { Handle, Position, type NodeProps } from '@xyflow/svelte';

	type $$Props = NodeProps;
	export let data: $$Props['data'];

	// data.label, data.type, data.tools, data.status
	$: label = data?.label ?? '';
	$: nodeType = data?.nodeType ?? 'agent';
	$: tools = data?.tools ?? [];
	$: status = data?.status ?? 'done';
	$: isDeep = data?.round === 2; // Round 2 = critique

	const colors: Record<string, string> = {
		router: 'border-blue-400 dark:border-blue-600 bg-blue-50 dark:bg-blue-950',
		agent: 'border-emerald-400 dark:border-emerald-600 bg-emerald-50 dark:bg-emerald-950',
		synthesis: 'border-purple-400 dark:border-purple-600 bg-purple-50 dark:bg-purple-950',
		output: 'border-amber-400 dark:border-amber-600 bg-amber-50 dark:bg-amber-950',
		critique: 'border-orange-400 dark:border-orange-600 bg-orange-50 dark:bg-orange-950'
	};

	$: colorClass = colors[nodeType] ?? colors.agent;
</script>

<div
	class="px-3 py-2 shadow-md rounded-xl border-2 {colorClass} w-52 group {isDeep ? 'border-dashed' : ''}"
>
	<Handle type="target" position={Position.Top} class="!bg-gray-400" />

	<div class="flex items-center gap-2">
		<div class="text-sm font-semibold line-clamp-1">{label}</div>
	</div>

	{#if tools.length > 0}
		<div class="flex flex-wrap gap-1 mt-1">
			{#each tools as tool}
				<span class="text-[10px] px-1.5 py-0.5 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
					🔧 {tool}
				</span>
			{/each}
		</div>
	{/if}

	{#if isDeep}
		<div class="text-[10px] text-orange-500 mt-0.5 font-medium">Round 2 · Peer Review</div>
	{/if}

	<Handle type="source" position={Position.Bottom} class="!bg-gray-400" />
</div>
