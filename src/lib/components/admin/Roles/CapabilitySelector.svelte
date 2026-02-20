<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import Switch from '$lib/components/common/Switch.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let capabilities: string[] = [];
	export let selectedCapabilities: string[] = [];

	// Capability metadata: display name, description, and group
	// Keys match the dotted capability keys from the backend (SYSTEM_CAPABILITIES)
	const CAPABILITY_META: Record<string, { label: string; description: string; group: string }> = {
		// Admin tier — User & System Management
		'admin.manage_users': {
			label: 'Manage Users',
			description: 'Create, update, and delete user accounts',
			group: 'Administration'
		},
		'admin.manage_groups': {
			label: 'Manage Groups',
			description: 'Create and manage user groups and their permissions',
			group: 'Administration'
		},
		'admin.manage_roles': {
			label: 'Manage Roles',
			description: 'Create, edit, and assign custom roles',
			group: 'Administration'
		},
		'admin.manage_connections': {
			label: 'Manage Connections',
			description: 'Configure Ollama, OpenAI, and other LLM provider connections',
			group: 'Administration'
		},
		'admin.manage_config': {
			label: 'Manage Configuration',
			description: 'Access and modify system-wide configuration',
			group: 'Administration'
		},
		'admin.manage_pipelines': {
			label: 'Manage Pipelines',
			description: 'Create, update, and delete pipelines',
			group: 'Administration'
		},
		'admin.manage_functions': {
			label: 'Manage Functions',
			description: 'Create, update, and delete custom functions',
			group: 'Administration'
		},
		'admin.manage_evaluations': {
			label: 'Manage Evaluations',
			description: 'Configure and run model evaluations and leaderboards',
			group: 'Administration'
		},
		'admin.bypass_access_control': {
			label: 'Bypass Access Control',
			description: 'Access workspace content regardless of ownership',
			group: 'Administration'
		},
		// Audit tier
		'audit.read_user_chats': {
			label: 'Read User Chats',
			description: 'Read-only access to all user chat conversations',
			group: 'Audit & Compliance'
		},
		'audit.view_analytics': {
			label: 'View Analytics',
			description: 'Access analytics dashboard and usage statistics',
			group: 'Audit & Compliance'
		},
		'audit.export_data': {
			label: 'Export Data',
			description: 'Export chats, analytics, and system data',
			group: 'Audit & Compliance'
		},
		// Workspace delegation tier
		'workspace.manage_all_models': {
			label: 'Manage All Models',
			description: 'Manage all models regardless of ownership',
			group: 'Workspace'
		},
		'workspace.manage_all_knowledge': {
			label: 'Manage All Knowledge',
			description: 'Manage all knowledge bases regardless of ownership',
			group: 'Workspace'
		},
		'workspace.manage_all_tools': {
			label: 'Manage All Tools',
			description: 'Manage all tools regardless of ownership',
			group: 'Workspace'
		},
		'workspace.manage_all_prompts': {
			label: 'Manage All Prompts',
			description: 'Manage all prompts regardless of ownership',
			group: 'Workspace'
		},
		'workspace.manage_all_skills': {
			label: 'Manage All Skills',
			description: 'Manage all skills regardless of ownership',
			group: 'Workspace'
		},
		'workspace.manage_all_spaces': {
			label: 'Manage All Spaces',
			description: 'Manage all spaces regardless of ownership',
			group: 'Workspace'
		},
		'workspace.manage_all_files': {
			label: 'Manage All Files',
			description: 'Manage all files regardless of ownership',
			group: 'Workspace'
		},
		'workspace.manage_all_channels': {
			label: 'Manage All Channels',
			description: 'Manage all channels regardless of ownership',
			group: 'Workspace'
		}
	};

	// Group capabilities into sections
	$: groupedCapabilities = capabilities.reduce(
		(acc, cap) => {
			const meta = CAPABILITY_META[cap];
			const group = meta?.group ?? 'Other';
			if (!acc[group]) acc[group] = [];
			acc[group].push(cap);
			return acc;
		},
		{} as Record<string, string[]>
	);

	const toggle = (cap: string) => {
		if (selectedCapabilities.includes(cap)) {
			selectedCapabilities = selectedCapabilities.filter((c) => c !== cap);
		} else {
			selectedCapabilities = [...selectedCapabilities, cap];
		}
	};

	const isSelected = (cap: string) => selectedCapabilities.includes(cap);

	const getLabel = (cap: string) =>
		CAPABILITY_META[cap]?.label ?? cap.split('.').pop()?.replace(/_/g, ' ') ?? cap;
	const getDescription = (cap: string) => CAPABILITY_META[cap]?.description ?? '';

	const GROUP_ORDER = ['Administration', 'Audit & Compliance', 'Workspace', 'Other'];

	$: sortedGroups = GROUP_ORDER.filter((g) => groupedCapabilities[g]);
</script>

<div class="space-y-4">
	{#if capabilities.length === 0}
		<div
			class="flex flex-col items-center justify-center py-8 text-sm text-gray-400 dark:text-gray-600"
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="1.5"
				stroke-linecap="round"
				stroke-linejoin="round"
				class="size-8 mb-2 opacity-50"
			>
				<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
			</svg>
			{$i18n.t('No capabilities available')}
		</div>
	{:else}
		{#each sortedGroups as group}
			{#if groupedCapabilities[group]}
				<div>
					<div
						class="mb-1.5 text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500"
					>
						{$i18n.t(group)}
					</div>

					<div class="space-y-0.5">
						{#each groupedCapabilities[group] as cap}
							<div class="flex w-full items-center justify-between py-1.5">
								<div class="flex flex-col pr-4">
									<span class="text-sm font-medium text-gray-800 dark:text-gray-200">
										{getLabel(cap)}
									</span>
									{#if getDescription(cap)}
										<span class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
											{$i18n.t(getDescription(cap))}
										</span>
									{/if}
								</div>
								<Switch state={isSelected(cap)} on:change={() => toggle(cap)} />
							</div>
						{/each}
					</div>
				</div>

				{#if group !== sortedGroups[sortedGroups.length - 1]}
					<hr class="border-gray-100/50 dark:border-gray-850/50" />
				{/if}
			{/if}
		{/each}
	{/if}
</div>
