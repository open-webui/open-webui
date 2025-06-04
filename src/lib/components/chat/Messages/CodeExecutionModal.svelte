<script lang="ts">
	import { getContext } from 'svelte';
	import CodeBlock from './CodeBlock.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	const i18n = getContext('i18n');

	export let show = false;
	export let codeExecution = null;
</script>

<Modal size="lg" bind:show>
	<div>
		<div class="flex justify-between dark:text-gray-300 px-5 pt-4 pb-2">
			<div class="text-lg font-medium self-center flex flex-col gap-0.5 capitalize">
				{#if codeExecution?.result}
					<div>
						{#if codeExecution.result?.error}
							<Badge type="error" content="error" />
						{:else if codeExecution.result?.output}
							<Badge type="success" content="success" />
						{:else}
							<Badge type="warning" content="incomplete" />
						{/if}
					</div>
				{/if}

				<div class="flex gap-2 items-center">
					{#if !codeExecution?.result}
						<div>
							<Spinner className="size-4" />
						</div>
					{/if}

					<div>
						{#if codeExecution?.name}
							{$i18n.t('Code execution')}: {codeExecution?.name}
						{:else}
							{$i18n.t('Code execution')}
						{/if}
					</div>
				</div>
			</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
					codeExecution = null;
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-4 pb-5">
			<div
				class="flex flex-col w-full dark:text-gray-200 overflow-y-scroll max-h-[22rem] scrollbar-hidden"
			>
				<div class="flex flex-col w-full">
					<CodeBlock
						id="code-exec-{codeExecution?.id}-code"
						lang={codeExecution?.language ?? ''}
						code={codeExecution?.code ?? ''}
						className=""
						editorClassName={codeExecution?.result &&
						(codeExecution?.result?.error || codeExecution?.result?.output)
							? 'rounded-b-none'
							: ''}
						stickyButtonsClassName="top-0"
						run={false}
					/>
				</div>

				{#if codeExecution?.result && (codeExecution?.result?.error || codeExecution?.result?.output)}
					<div class="dark:bg-[#202123] dark:text-white px-4 py-4 rounded-b-lg flex flex-col gap-3">
						{#if codeExecution?.result?.error}
							<div>
								<div class=" text-gray-500 text-xs mb-1">{$i18n.t('ERROR')}</div>
								<div class="text-sm">{codeExecution?.result?.error}</div>
							</div>
						{/if}
						{#if codeExecution?.result?.output}
							<div>
								<div class=" text-gray-500 text-xs mb-1">{$i18n.t('OUTPUT')}</div>
								<div class="text-sm">{codeExecution?.result?.output}</div>
							</div>
						{/if}
					</div>
				{/if}
				{#if codeExecution?.result?.files && codeExecution?.result?.files.length > 0}
					<div class="flex flex-col w-full">
						<hr class="border-gray-100 dark:border-gray-850 my-2" />
						<div class=" text-sm font-medium dark:text-gray-300">
							{$i18n.t('Files')}
						</div>
						<ul class="mt-1 list-disc pl-4 text-xs">
							{#each codeExecution?.result?.files as file}
								<li>
									<a href={file.url} target="_blank">{file.name}</a>
								</li>
							{/each}
						</ul>
					</div>
				{/if}
			</div>
		</div>
	</div>
</Modal>
