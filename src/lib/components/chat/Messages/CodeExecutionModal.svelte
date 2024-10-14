<script lang="ts">
	import { getContext } from 'svelte';
	import CodeBlock from './CodeBlock.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	const i18n = getContext('i18n');

	export let show = false;
	export let code_execution = null;
</script>

<Modal size="lg" bind:show>
	<div>
		<div class="flex justify-between dark:text-gray-300 px-5 pt-4 pb-2">
			<div class="text-lg font-medium self-center capitalize">
				{#if code_execution?.status == 'OK'}
					&#x2705; <!-- Checkmark -->
				{:else if code_execution?.status == 'ERROR'}
					&#x274C; <!-- X mark -->
				{:else if code_execution?.status == 'PENDING'}
					&#x23F3; <!-- Hourglass -->
				{:else}
					&#x2049;&#xFE0F; <!-- Interrobang -->
				{/if}
				{#if code_execution?.name}
					{$i18n.t('Code execution')}: {code_execution?.name}
				{:else}
					{$i18n.t('Code execution')}
				{/if}
			</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
					code_execution = null;
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

		<div class="flex flex-col md:flex-row w-full px-6 pb-5 md:space-x-4">
			<div
				class="flex flex-col w-full dark:text-gray-200 overflow-y-scroll max-h-[22rem] scrollbar-hidden"
			>
				<div class="flex flex-col w-full">
					<div class="text-sm font-medium dark:text-gray-300">
						{$i18n.t('Code')}
					</div>

					<CodeBlock
						id="codeexec-{code_execution?.uuid}-code"
						lang={code_execution?.language}
						code={code_execution?.code}
						allow_execution={false}
					/>
				</div>
				{#if code_execution?.error}
					<div class="flex flex-col w-full">
						<hr class=" dark:border-gray-850 my-3" />
						<div class="text-sm dark:text-gray-400">
							{$i18n.t('Error')}
						</div>

						<CodeBlock
							id="codeexec-{code_execution?.uuid}-error"
							lang=""
							code={code_execution?.error}
							allow_execution={false}
						/>
					</div>
				{/if}
				{#if code_execution?.output}
					<div class="flex flex-col w-full">
						<hr class=" dark:border-gray-850 my-3" />
						<div class="text-sm dark:text-gray-400">
							{$i18n.t('Output')}
						</div>

						<CodeBlock
							id="codeexec-{code_execution?.uuid}-output"
							lang=""
							code={code_execution?.output}
							allow_execution={false}
						/>
					</div>
				{/if}
				{#if code_execution?.files && code_execution?.files.length > 0}
					<div class="flex flex-col w-full">
						<hr class=" dark:border-gray-850 my-3" />
						<div class=" text-sm font-medium dark:text-gray-300">
							{$i18n.t('Files')}
						</div>
						<ul class="mt-1 list-disc pl-4 text-xs">
							{#each code_execution?.files as file}
								<li>
									&#x1F4BE; <!-- Floppy disk -->
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
