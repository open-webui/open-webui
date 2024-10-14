<script lang="ts">
	import CodeExecutionModal from './CodeExecutionModal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	export let code_executions = [];

	let _code_executions = [];

	$: _code_executions = code_executions.reduce((acc, code_execution) => {
		let error = null;
		let output = null;
		let files = [];
		let status = 'PENDING';

		if (code_execution.result) {
			output = code_execution.result.output;
			if (code_execution.result.error) {
				status = 'ERROR';
				error = code_execution.result.error;
			} else {
				status = 'OK';
			}
			if (code_execution.result.files) {
				files = code_execution.result.files;
			}
		}

		acc.push({
			id: code_execution.id,
			name: code_execution.name,
			code: code_execution.code,
			language: code_execution.language || '',
			status: status,
			error: error,
			output: output,
			files: files
		});
		return acc;
	}, []);

	let selectedCodeExecution = null;
	let showCodeExecutionModal = false;
</script>

<CodeExecutionModal bind:show={showCodeExecutionModal} code_execution={selectedCodeExecution} />

{#if _code_executions.length > 0}
	<div class="mt-1 mb-2 w-full flex gap-1 items-center flex-wrap">
		{#each _code_executions as code_execution}
			<div class="flex gap-1 text-xs font-semibold">
				<button
					class="flex dark:text-gray-300 py-1 px-1 bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-xl max-w-96"
					on:click={() => {
						selectedCodeExecution = code_execution;
						showCodeExecutionModal = true;
					}}
				>
					<div class="bg-white dark:bg-gray-700 rounded-full size-4">
						{#if code_execution.status == 'OK'}
							&#x2705; <!-- Checkmark -->
						{:else if code_execution.status == 'ERROR'}
							&#x274C; <!-- X mark -->
						{:else if code_execution.status == 'PENDING'}
							<Spinner className="size-4" />
						{:else}
							&#x2049;&#xFE0F; <!-- Interrobang -->
						{/if}
					</div>
					<div
						class="flex-1 mx-2 line-clamp-1 code-execution-name {code_execution.status == 'PENDING'
							? 'pulse'
							: ''}"
					>
						{code_execution.name}
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
