<script lang="ts">
	import { getContext } from 'svelte';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { marked } from 'marked';

	const i18n = getContext('i18n');

	const toolLabels = {
		time: {
			label: $i18n.t('Time & Calculation'),
			description: $i18n.t('Get current time and perform date/time calculations')
		},
		memory: {
			label: $i18n.t('Memory'),
			description: $i18n.t('Search and manage user memories')
		},
		chats: {
			label: $i18n.t('Chat History'),
			description: $i18n.t('Search and view user chat history')
		},
		notes: {
			label: $i18n.t('Notes'),
			description: $i18n.t('Search, view, and manage user notes')
		},
		knowledge: {
			label: $i18n.t('Knowledge Base'),
			description: $i18n.t('Browse and query knowledge bases')
		},
		channels: {
			label: $i18n.t('Channels'),
			description: $i18n.t('Search channels and channel messages')
		},
		web_search: {
			label: $i18n.t('Web Search'),
			description: $i18n.t('Search the web and fetch URLs')
		},
		image_generation: {
			label: $i18n.t('Image Generation'),
			description: $i18n.t('Generate and edit images')
		},
		code_interpreter: {
			label: $i18n.t('Code Interpreter'),
			description: $i18n.t('Execute code')
		},
		tasks: {
			label: $i18n.t('Task Management'),
			description: $i18n.t('Break down complex requests into trackable steps')
		},
		automations: {
			label: $i18n.t('Automations'),
			description: $i18n.t('Create and manage scheduled automations')
		},
		calendar: {
			label: $i18n.t('Calendar'),
			description: $i18n.t('List calendars, search, create, update, and delete calendar events')
		},
		subagents: {
			label: $i18n.t('Sub-agents'),
			description: $i18n.t('Delegate focused work to parallel sub-agents')
		}
	};

	const allTools = Object.keys(toolLabels) as Array<keyof typeof toolLabels>;

	export let builtinTools: Record<string, boolean> = {};
</script>

<div>
	<div class="mb-1.5 text-xs text-gray-400 dark:text-gray-600">{$i18n.t('Builtin Tools')}</div>
	<div class="grid grid-cols-1 gap-x-5 gap-y-1 sm:grid-cols-2 lg:grid-cols-3">
		{#each allTools as tool}
			<div class="flex min-h-6 items-center justify-between gap-2.5">
				<div class="min-w-0 text-xs text-gray-600 dark:text-gray-400">
					<Tooltip content={marked.parse(toolLabels[tool].description)}>
						<span class="truncate">{$i18n.t(toolLabels[tool].label)}</span>
					</Tooltip>
				</div>
				<Checkbox
					state={builtinTools[tool] !== false ? 'checked' : 'unchecked'}
					on:change={(e) => {
						if (e.detail === 'checked') {
							delete builtinTools[tool];
						} else {
							builtinTools[tool] = false;
						}
						builtinTools = builtinTools;
					}}
				/>
			</div>
		{/each}
	</div>
</div>
