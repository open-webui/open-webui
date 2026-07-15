<script lang="ts">
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import DocumentArrowDown from '$lib/components/icons/DocumentArrowDown.svelte';
	import DocumentArrowUp from '$lib/components/icons/DocumentArrowUp.svelte';
	import Link from '$lib/components/icons/Link.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';

	type SplitCreateAction = {
		id: string;
		label: string;
		href?: string;
		onClick?: () => void | Promise<void>;
		visible?: boolean;
	};

	export let actions: SplitCreateAction[] = [];
	export let label = 'Create';

	const i18n = getContext<Writable<i18nType>>('i18n');

	let showMenu = false;
	$: visibleActions = actions.filter((action) => action.visible ?? true);
	$: primaryAction =
		visibleActions.find((action) => action.id.endsWith('-new')) ?? visibleActions[0] ?? null;

	const runAction = async (action: SplitCreateAction | null) => {
		if (!action) return;
		if (action.href) {
			await goto(action.href);
		} else {
			await action.onClick?.();
		}
	};

	const getActionIcon = (id: string) => {
		if (id.endsWith('-new')) return Pencil;
		if (id.includes('-import-link')) return Link;
		if (id.includes('-import')) return DocumentArrowUp;
		if (id.includes('-export')) return DocumentArrowDown;
		return Pencil;
	};
</script>

{#if visibleActions.length}
	<div
		class="ml-1 flex overflow-hidden rounded-lg bg-gray-50 text-xs text-gray-900 transition ring-1 ring-gray-200 dark:bg-gray-850 dark:text-gray-100 dark:ring-gray-800"
	>
		<button
			class="px-2.5 py-1 transition hover:bg-gray-100 dark:hover:bg-gray-800"
			on:click={() => {
				runAction(primaryAction);
			}}
		>
			{$i18n.t(label)}
		</button>

		<Dropdown bind:show={showMenu} align="end" sideOffset={6}>
			<button
				class="flex items-center border-l border-gray-200 px-1.5 py-1 transition hover:bg-gray-100 dark:border-gray-800 dark:hover:bg-gray-800"
				aria-label={$i18n.t('Open create menu')}
			>
				<ChevronDown className="size-2.5" strokeWidth="2.5" />
			</button>

			<div slot="content">
				<DropdownMenu className="min-w-[170px]">
					{#each visibleActions as action (action.id)}
						{@const Icon = getActionIcon(action.id)}
						{#if action.href}
							<a
								href={action.href}
								on:click={() => {
									showMenu = false;
								}}
							>
								<Icon className="size-3.5" />
								<span class="self-center truncate">{action.label}</span>
							</a>
						{:else}
							<button
								on:click={async () => {
									await action.onClick?.();
									showMenu = false;
								}}
							>
								<Icon className="size-3.5" />
								<span class="self-center truncate">{action.label}</span>
							</button>
						{/if}
					{/each}
				</DropdownMenu>
			</div>
		</Dropdown>
	</div>
{/if}
