<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { marked } from 'marked';

	const i18n: Writable<i18nType> = getContext('i18n');

	let toolLabels;
	$: toolLabels = {
		time: {
			label: $i18n.t('settings.admin.models.builtinTools.time.label'),
			description: $i18n.t('settings.admin.models.builtinTools.time.description')
		},
		user_input: {
			label: $i18n.t('settings.admin.models.builtinTools.userInput.label'),
			description: $i18n.t('settings.admin.models.builtinTools.userInput.description')
		},
		memory: {
			label: $i18n.t('settings.admin.models.builtinTools.memory.label'),
			description: $i18n.t('settings.admin.models.builtinTools.memory.description')
		},
		chats: {
			label: $i18n.t('settings.admin.models.builtinTools.chats.label'),
			description: $i18n.t('settings.admin.models.builtinTools.chats.description')
		},
		notes: {
			label: $i18n.t('settings.admin.models.builtinTools.notes.label'),
			description: $i18n.t('settings.admin.models.builtinTools.notes.description')
		},
		knowledge: {
			label: $i18n.t('settings.admin.models.builtinTools.knowledge.label'),
			description: $i18n.t('settings.admin.models.builtinTools.knowledge.description')
		},
		files: {
			label: $i18n.t('settings.admin.models.builtinTools.files.label'),
			description: $i18n.t('settings.admin.models.builtinTools.files.description')
		},
		channels: {
			label: $i18n.t('settings.admin.models.builtinTools.channels.label'),
			description: $i18n.t('settings.admin.models.builtinTools.channels.description')
		},
		notifications: {
			label: $i18n.t('settings.admin.models.builtinTools.notifications.label'),
			description: $i18n.t('settings.admin.models.builtinTools.notifications.description')
		},
		web_search: {
			label: $i18n.t('settings.admin.models.builtinTools.webSearch.label'),
			description: $i18n.t('settings.admin.models.builtinTools.webSearch.description')
		},
		image_generation: {
			label: $i18n.t('settings.admin.models.builtinTools.imageGeneration.label'),
			description: $i18n.t('settings.admin.models.builtinTools.imageGeneration.description')
		},
		code_interpreter: {
			label: $i18n.t('settings.admin.models.builtinTools.codeInterpreter.label'),
			description: $i18n.t('settings.admin.models.builtinTools.codeInterpreter.description')
		},
		tasks: {
			label: $i18n.t('settings.admin.models.builtinTools.tasks.label'),
			description: $i18n.t('settings.admin.models.builtinTools.tasks.description')
		},
		automations: {
			label: $i18n.t('settings.admin.models.builtinTools.automations.label'),
			description: $i18n.t('settings.admin.models.builtinTools.automations.description')
		},
		calendar: {
			label: $i18n.t('settings.admin.models.builtinTools.calendar.label'),
			description: $i18n.t('settings.admin.models.builtinTools.calendar.description')
		},
		subagents: {
			label: $i18n.t('settings.admin.models.builtinTools.subagents.label'),
			description: $i18n.t('settings.admin.models.builtinTools.subagents.description')
		}
	};

	$: allTools = Object.keys(toolLabels ?? {}) as Array<keyof typeof toolLabels>;

	export let builtinTools: Record<string, boolean> = {};

	const setBuiltinTool = (tool: keyof typeof toolLabels, checked: boolean) => {
		if (checked) {
			delete builtinTools[tool];
		} else {
			builtinTools[tool] = false;
		}
		builtinTools = builtinTools;
	};
</script>

<div>
	<div class="mb-1.5 text-xs text-gray-400 dark:text-gray-600">
		{$i18n.t('settings.admin.models.builtinTools.title')}
	</div>
	<div class="grid grid-cols-1 gap-x-5 gap-y-1 sm:grid-cols-2 lg:grid-cols-3">
		{#each allTools as tool}
			<div class="flex min-h-6 items-center gap-2.5">
				<Checkbox
					ariaLabel={$i18n.t(toolLabels[tool].label)}
					state={builtinTools[tool] !== false ? 'checked' : 'unchecked'}
					on:change={(e) => {
						setBuiltinTool(tool, e.detail === 'checked');
					}}
				/>
				<button
					type="button"
					class="min-w-0 cursor-pointer text-left text-xs text-gray-600 dark:text-gray-400"
					on:click={() => setBuiltinTool(tool, builtinTools[tool] === false)}
				>
					<Tooltip
						as="span"
						className="block min-w-0"
						content={marked.parse(toolLabels[tool].description)}
					>
						<span class="block truncate">{$i18n.t(toolLabels[tool].label)}</span>
					</Tooltip>
				</button>
			</div>
		{/each}
	</div>
</div>
