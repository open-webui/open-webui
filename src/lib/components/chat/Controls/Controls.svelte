<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import XMark from '$lib/components/icons/XMark.svelte';
	import AdvancedParams from '../Settings/Advanced/AdvancedParams.svelte';
	import Valves from '$lib/components/chat/Controls/Valves.svelte';
	import FileItem from '$lib/components/common/FileItem.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';

	import { user, settings } from '$lib/stores';
	import { onMount } from 'svelte';

	const ENTITY_TYPES = [
		{ key: 'PERSON',        label: 'Name / Person' },
		{ key: 'ORGANIZATION',  label: 'Organization' },
		{ key: 'EMAIL_ADDRESS', label: 'Email' },
		{ key: 'IBAN_CODE',     label: 'IBAN' },
		{ key: 'PHONE_NUMBER',  label: 'Phone Number' },
		{ key: 'ID',            label: 'ID' },
	];

	let entityToggles: Record<string, boolean> = {};

	onMount(() => {
		const saved = localStorage.getItem('garnet_entity_toggles');
		if (saved) {
			entityToggles = JSON.parse(saved);
		} else {
			ENTITY_TYPES.forEach(e => (entityToggles[e.key] = true));
			localStorage.setItem('garnet_entity_toggles', JSON.stringify(entityToggles));
		}
	});

	function onEntityChange(key: string, value: string) {
		entityToggles[key] = value === 'on';
		localStorage.setItem('garnet_entity_toggles', JSON.stringify(entityToggles));
		entityToggles = { ...entityToggles };
	}
	export let models = [];
	export let chatFiles = [];
	export let params = {};
	export let embed = false;

	// Persist collapsible section open/close state
	const getOpen = (key: string, fallback = true): boolean => {
		const v = localStorage.getItem(`chatControls.${key}`);
		return v !== null ? v === 'true' : fallback;
	};
	const setOpen = (key: string) => (open: boolean) => {
		localStorage.setItem(`chatControls.${key}`, String(open));
	};

	let showFiles = getOpen('files');
	let showValves = getOpen('valves', false);
	let showSystemPrompt = getOpen('systemPrompt');
	let showAdvancedParams = getOpen('advancedParams');
	let showGarnet = getOpen('garnet', true);
</script>

<div class=" dark:text-white">
	{#if !embed}
		<div class=" flex items-center justify-between dark:text-gray-100 mb-2">
			<div class=" text-md self-center font-primary">{$i18n.t('Controls')}</div>
			<button
				class="self-center"
				aria-label={$i18n.t('Close chat controls')}
				on:click={() => {
					dispatch('close');
				}}
			>
				<XMark className="size-3.5" />
			</button>
		</div>
	{/if}

	{#if $user?.role === 'admin' || ($user?.permissions.chat?.controls ?? true)}
		<div class=" dark:text-gray-200 text-sm py-0.5 px-0.5">
			{#if chatFiles.length > 0}
				<Collapsible
					title={$i18n.t('Files')}
					bind:open={showFiles}
					onChange={setOpen('files')}
					buttonClassName="w-full"
				>
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
				<Collapsible
					bind:open={showValves}
					onChange={setOpen('valves')}
					title={$i18n.t('Valves')}
					buttonClassName="w-full"
				>
					<div class="text-sm" slot="content">
						<Valves show={showValves} />
					</div>
				</Collapsible>

				<hr class="my-2 border-gray-50 dark:border-gray-700/10" />
			{/if}

			{#if $user?.role === 'admin' || ($user?.permissions.chat?.system_prompt ?? true)}
				<Collapsible
					title={$i18n.t('System Prompt')}
					bind:open={showSystemPrompt}
					onChange={setOpen('systemPrompt')}
					buttonClassName="w-full"
				>
					<div class="" slot="content">
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
				<Collapsible
					title={$i18n.t('Advanced Params')}
					bind:open={showAdvancedParams}
					onChange={setOpen('advancedParams')}
					buttonClassName="w-full"
				>
					<div class="text-sm mt-1.5" slot="content">
						<div>
							<AdvancedParams admin={$user?.role === 'admin'} custom={true} bind:params />
						</div>
					</div>
				</Collapsible>
			{/if}

			<hr class="my-2 border-gray-50 dark:border-gray-700/10" />

			<Collapsible
				title={$i18n.t('Garnet')}
				bind:open={showGarnet}
				onChange={setOpen('garnet')}
				buttonClassName="w-full"
			>
				<div class="text-sm mt-1.5" slot="content">
					<div class="w-full rounded-lg overflow-hidden border border-gray-700">
						<div class="grid grid-cols-2 bg-gray-700 px-3 py-1.5">
							<span class="text-xs font-semibold uppercase tracking-wider text-gray-300">Entity Type</span>
							<span class="text-xs font-semibold uppercase tracking-wider text-gray-300 text-right">Detection</span>
						</div>
						{#each ENTITY_TYPES as entity, i}
							<div class="grid grid-cols-2 items-center px-3 py-2
									{i % 2 === 0 ? 'bg-gray-800' : 'bg-gray-900'}
									border-b border-gray-700 last:border-0">
								<span class="text-xs text-white">{entity.label}</span>
								<div class="flex justify-end">
									<select
										value={entityToggles[entity.key] ? 'on' : 'off'}
										on:change={(e) => onEntityChange(entity.key, e.currentTarget.value)}
										class="bg-gray-700 text-white text-xs rounded px-2 py-1
											   border border-gray-600 focus:outline-none focus:border-blue-500
											   cursor-pointer min-w-[70px]"
									>
										<option value="on">On</option>
										<option value="off">Off</option>
									</select>
								</div>
							</div>
						{/each}
					</div>
				</div>
			</Collapsible>
		</div>
	{/if}
</div>
