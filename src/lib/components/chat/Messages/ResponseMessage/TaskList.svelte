<script lang="ts">
	import { getContext } from 'svelte';
	import { slide } from 'svelte/transition';
	import TaskListIcon from '$lib/components/icons/TaskList.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';

	const i18n = getContext('i18n');

	export let tasks: Array<{ id: string; content: string; status: string }> = [];

	let collapsed = false;

	$: completedCount = tasks.filter((t) => t.status === 'completed').length;
	$: totalCount = tasks.length;
	$: hasActive = tasks.some((t) => t.status === 'pending' || t.status === 'in_progress');
</script>

{#if tasks.length > 0 && hasActive}
	<div
		class="my-2 rounded-2xl border border-gray-50 dark:border-gray-850 bg-white dark:bg-gray-900"
		transition:slide={{ duration: 200 }}
	>
		<!-- Header -->
		<div class="flex items-center justify-between px-3.5 py-2">
			<div class="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400">
				<TaskListIcon className="w-3.5 h-3.5" />
				<span>
					{completedCount}
					{$i18n.t('out of')}
					{totalCount}
					{$i18n.t('tasks completed')}
				</span>
			</div>

			<button
				class="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
				on:click={() => (collapsed = !collapsed)}
				aria-label={collapsed ? 'Expand' : 'Collapse'}
			>
				{#if collapsed}
					<ChevronUp className="w-2.5 h-2.5" />
				{:else}
					<ChevronDown className="w-2.5 h-2.5" />
				{/if}
			</button>
		</div>

		<!-- Task list -->
		{#if !collapsed}
			<div class="px-3.5 pb-2.5 space-y-0.5" transition:slide={{ duration: 150 }}>
				{#each tasks as task, idx (task.id)}
					<div class="flex items-start gap-2 py-0.5 text-xs">
						<span class="flex-shrink-0 mt-0.5 text-gray-400 dark:text-gray-500">
							{#if task.status === 'completed'}
								<svg
									class="w-3.5 h-3.5"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2.5"
								>
									<path d="M5 13l4 4L19 7" stroke-linecap="round" stroke-linejoin="round" />
								</svg>
							{:else if task.status === 'in_progress'}
								<svg
									class="w-3.5 h-3.5 animate-spin"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2.5"
								>
									<path d="M12 3a9 9 0 1 0 9 9" stroke-linecap="round" />
								</svg>
							{:else if task.status === 'cancelled'}
								<svg
									class="w-3.5 h-3.5"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2"
								>
									<circle cx="12" cy="12" r="9" stroke-dasharray="4 3" />
								</svg>
							{:else}
								<svg
									class="w-3.5 h-3.5"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2"
								>
									<circle cx="12" cy="12" r="9" />
								</svg>
							{/if}
						</span>
						<span
							class="line-clamp-2 {task.status === 'completed'
								? 'line-through text-gray-400 dark:text-gray-500'
								: task.status === 'cancelled'
									? 'line-through text-gray-400 dark:text-gray-600'
									: 'text-gray-700 dark:text-gray-300'}"
						>
							{idx + 1}. {task.content}
						</span>
					</div>
				{/each}
			</div>
		{/if}
	</div>
{/if}
