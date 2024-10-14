<script lang="ts">
	import CodeExecutionModal from './CodeExecutionModal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	export let codeExecutions = [];

	let selectedCodeExecution = null;
	let showCodeExecutionModal = false;
</script>

<CodeExecutionModal bind:show={showCodeExecutionModal} codeExecution={selectedCodeExecution} />

{#if codeExecutions.length > 0}
	<div class="mt-1 mb-2 w-full flex gap-1 items-center flex-wrap">
		{#each codeExecutions.map((execution) => {
			let error = null;
			let output = null;
			let files = [];
			let status = 'PENDING';

			if (execution.result) {
				output = execution.result.output;
				if (execution.result.error) {
					status = 'ERROR';
					error = execution.result.error;
				} else {
					status = 'OK';
				}
				if (execution.result.files) {
					files = execution.result.files;
				}
			}

			return { id: execution.id, name: execution.name, code: execution.code, language: execution.language || '', status: status, error: error, output: output, files: files };
		}) as execution (execution.id)}
			<div class="flex gap-1 text-xs font-semibold">
				<button
					class="flex dark:text-gray-300 py-1 px-1 bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-xl max-w-96"
					on:click={() => {
						selectedCodeExecution = execution;
						showCodeExecutionModal = true;
					}}
				>
					<div class="bg-white dark:bg-gray-700 rounded-full size-4">
						{#if execution.status == 'OK'}
							&#x2705; <!-- Checkmark -->
						{:else if execution.status == 'ERROR'}
							&#x274C; <!-- X mark -->
						{:else if execution.status == 'PENDING'}
							<Spinner className="size-4" />
						{:else}
							&#x2049;&#xFE0F; <!-- Interrobang -->
						{/if}
					</div>
					<div
						class="flex-1 mx-2 line-clamp-1 code-execution-name {execution.status == 'PENDING'
							? 'pulse'
							: ''}"
					>
						{execution.name}
					</div>
				</button>
			</div>
		{/each}
	</div>
{/if}

<style>
	@keyframes pulse {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.6;
		}
	}

	.pulse {
		opacity: 1;
		animation: pulse 1.5s ease;
	}
</style>
