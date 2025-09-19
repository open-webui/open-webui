<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { getContext, onMount, tick } from 'svelte';
	import { get } from 'svelte/store';

	import { config, user } from '$lib/stores';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import WorkflowIcon from '$lib/components/icons/WorkflowIcon.svelte';

	const i18n = getContext('i18n');

	export let selectedWorkflowIds: string[] = [];
	export let onClose: Function;

	let workflows: Record<string, any> = {};
	let show = false;

	$: if (show) {
		init();
	}

	// 写死的数据
	const mockWorkflows = [
		{
			id: 'workflow-1',
			name: 'Test Workflow',
			description: 'A test workflow for demonstration'
		},
		{
			id: 'workflow-2',
			name: 'Data Processing Workflow',
			description: 'Process data through multiple steps'
		},
		{
			id: 'workflow-3',
			name: 'Content Generation Workflow',
			description: 'Generate content using AI models'
		}
	];

	const init = async () => {
		// 使用写死的数据
		workflows = mockWorkflows.reduce((a: Record<string, any>, workflow: any) => {
			a[workflow.id] = {
				name: workflow.name,
				description: workflow.description,
				enabled: selectedWorkflowIds.includes(workflow.id)
			};
			return a;
		}, {});
	};

	const selectWorkflow = (workflowId: string) => {
		workflows[workflowId].enabled = !workflows[workflowId].enabled;
	};
</script>

<Dropdown
	bind:show
	on:show={(e) => {
		if (e.detail === false) {
			onClose();
		}
	}}
>
		<Tooltip content="Select Workflow">
		<slot />
	</Tooltip>

	<div slot="content">
		<DropdownMenu.Content
			class="w-full max-w-[280px] rounded-xl px-1 py-1 border border-gray-300/30 dark:border-gray-700/50 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-sm"
			sideOffset={10}
			alignOffset={-8}
			side="top"
		>
			{#if Object.keys(workflows).length > 0}
				<div class="max-h-28 overflow-y-auto scrollbar-hidden">
					{#each Object.keys(workflows) as workflowId}
						<button
							class="flex w-full justify-between gap-2 items-center px-3 py-2 text-sm font-medium cursor-pointer rounded-xl"
							on:click={() => {
								selectWorkflow(workflowId);
							}}
						>
							<div class="flex-1 truncate">
								<Tooltip
									content={workflows[workflowId]?.description ?? ''}
									placement="top-start"
									className="flex flex-1 gap-2 items-center"
								>
									<div class="shrink-0">
										<WorkflowIcon className="size-4" strokeWidth="1.75" />
									</div>

									<div class="truncate">{workflows[workflowId].name}</div>
								</Tooltip>
							</div>

							<div class="shrink-0">
								<Switch
									state={workflows[workflowId].enabled}
									on:change={async (e) => {
										const state = e.detail;
										await tick();
										if (state) {
											selectedWorkflowIds = [...selectedWorkflowIds, workflowId];
										} else {
											selectedWorkflowIds = selectedWorkflowIds.filter((id) => id !== workflowId);
										}
									}}
								/>
							</div>
						</button>
					{/each}
				</div>

				<hr class="border-black/5 dark:border-white/5 my-1" />
			{/if}
		</DropdownMenu.Content>
	</div>
</Dropdown>
