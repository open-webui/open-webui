<script lang="ts">
	import { createEventDispatcher, getContext, onMount } from 'svelte';
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import XMark from '$lib/components/icons/XMark.svelte';
	import AdvancedParams from '../Settings/Advanced/AdvancedParams.svelte';
	import Valves from '$lib/components/chat/Controls/Valves.svelte';
	import FileItem from '$lib/components/common/FileItem.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';

	import { user, settings, prompts } from '$lib/stores';
	import { getPrompts } from '$lib/apis/prompts';

	export let models = [];
	export let chatFiles = [];
	export let params: any = {};

	let showValves = false;

	onMount(async () => {
		if (!$prompts) {
			const res = await getPrompts(localStorage.token);
			if (res) {
				prompts.set(res);
			}
		}
	});
</script>

<div class=" dark:text-white">
	<div class=" flex items-center justify-between dark:text-gray-100 mb-2">
		<div class=" text-lg font-medium self-center font-primary">{$i18n.t('Chat Controls')}</div>
		<button
			class="self-center"
			on:click={() => {
				dispatch('close');
			}}
		>
			<XMark className="size-3.5" />
		</button>
	</div>

	{#if $user?.role === 'admin' || ($user?.permissions.chat?.controls ?? true)}
		<div class=" dark:text-gray-200 text-sm font-primary py-0.5 px-0.5">
			{#if chatFiles.length > 0}
				<Collapsible title={$i18n.t('Files')} open={true} buttonClassName="w-full">
					<div class="flex flex-col gap-1 mt-1.5" slot="content">
						{#each chatFiles as file, fileIdx}
							<FileItem
								className="w-full"
								item={file}
								edit={true}
								url={file?.url ? file.url : null}
								name={file.name}
								type={file.type}
								size={file?.size}
								dismissible={true}
								small={true}
								on:dismiss={() => {
									// Remove the file from the chatFiles array

									chatFiles.splice(fileIdx, 1);
									chatFiles = chatFiles;
								}}
								on:click={() => {
									console.log(file);
								}}
							/>
						{/each}
					</div>
				</Collapsible>

				<hr class="my-2 border-gray-50 dark:border-gray-700/10" />
			{/if}

			{#if $user?.role === 'admin' || ($user?.permissions.chat?.valves ?? true)}
				<Collapsible bind:open={showValves} title={$i18n.t('Valves')} buttonClassName="w-full">
					<div class="text-sm" slot="content">
						<Valves show={showValves} />
					</div>
				</Collapsible>

				<hr class="my-2 border-gray-50 dark:border-gray-700/10" />
			{/if}

			{#if $user?.role === 'admin' || ($user?.permissions.chat?.system_prompt ?? true)}
				<Collapsible title={$i18n.t('System Prompt')} open={true} buttonClassName="w-full">
					<div class="" slot="content">
						{#if $prompts}
							<div class="flex flex-col gap-1 mb-2">
								<div class="text-xs text-gray-500">{$i18n.t('Load from Library')}</div>
								<select
									class="w-full text-xs bg-transparent border border-gray-100 dark:border-gray-800 rounded-lg p-1.5 outline-hidden"
									on:change={(e) => {
										const target = e.target as HTMLSelectElement;
										const selectedPrompt = $prompts.find((p) => p.command === target.value);
										if (selectedPrompt) {
											params.system = selectedPrompt.content;
										}
										target.value = ''; // Reset selection
									}}
								>
									<option value="" disabled selected>{$i18n.t('Select a prompt')}</option>
									{#each $prompts.filter((p) => p.command.includes('system') || true) as prompt}
										<option value={prompt.command} class="bg-gray-100 dark:bg-gray-700"
											>{prompt.title} ({prompt.command})</option
										>
									{/each}
								</select>
							</div>
						{/if}
						<textarea
							bind:value={params.system}
							class="w-full text-xs outline-hidden resize-vertical {$settings.highContrastMode
								? 'border-2 border-gray-300 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 p-2.5'
								: 'py-1.5 bg-transparent'}"
							rows="4"
							placeholder={$i18n.t('Enter system prompt')}
						/>
					</div>
				</Collapsible>

				<hr class="my-2 border-gray-50 dark:border-gray-700/10" />
			{/if}

			{#if $user?.role === 'admin' || ($user?.permissions.chat?.params ?? true)}
				<Collapsible title={$i18n.t('Advanced Params')} open={true} buttonClassName="w-full">
					<div class="text-sm mt-1.5" slot="content">
						<div>
							<AdvancedParams admin={$user?.role === 'admin'} custom={true} bind:params />
						</div>
					</div>
				</Collapsible>
			{/if}
		</div>
	{/if}
</div>
