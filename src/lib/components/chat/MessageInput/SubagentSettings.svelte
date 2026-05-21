<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { getContext } from 'svelte';

	import { flyAndScale } from '$lib/utils/transitions';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Knobs from '$lib/components/icons/Knobs.svelte';

	const i18n: any = getContext('i18n');

	export let subagentReasoningEffort: string = '';
	export let subagentServiceTier: string = '';
	// Resolved by the parent (MessageInput) from the effective subagent
	// model's `info.meta.service_tiers`, falling back to the canonical set.
	// We don't recompute it here so the dropdown stays in sync with whatever
	// model the user has selected — even if that changes mid-session.
	export let allowedServiceTiers: readonly string[] = ['default', 'flex', 'priority'];

	let show = false;

	$: hasOverride = !!(subagentReasoningEffort || subagentServiceTier);
</script>

<Dropdown bind:show closeOnOutsideClick={true}>
	<Tooltip content={$i18n.t('Subagent settings')} placement="top">
		<button
			type="button"
			class="relative p-2 flex items-center text-sm rounded-full transition-colors duration-300 focus:outline-hidden bg-transparent text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 border border-transparent hover:border-gray-200 dark:hover:border-gray-700"
			aria-label={$i18n.t('Subagent settings')}
		>
			<Knobs className="size-4" />
			{#if hasOverride}
				<span
					class="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-book-cloth dark:bg-book-cloth"
					aria-hidden="true"
				/>
			{/if}
		</button>
	</Tooltip>

	<div slot="content">
		<DropdownMenu.Content
			class="w-72 rounded-2xl px-3 py-3 border border-gray-100 dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg"
			sideOffset={8}
			side="top"
			align="start"
			transition={flyAndScale}
		>
			<div class="text-xs font-semibold text-gray-700 dark:text-gray-200 px-1 mb-2">
				{$i18n.t('Subagent settings')}
			</div>

			<div class="mb-3">
				<label
					for="subagent-settings-reasoning"
					class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1 px-1"
				>
					{$i18n.t('Reasoning effort')}
				</label>
				<select
					id="subagent-settings-reasoning"
					bind:value={subagentReasoningEffort}
					class="w-full rounded-lg py-1.5 px-3 text-sm bg-gray-50 dark:bg-gray-900 dark:text-gray-100 outline-hidden border-hairline border-gray-200 dark:border-gray-700"
				>
					<option value="">{$i18n.t('default (admin)')}</option>
					<option value="minimal">minimal</option>
					<option value="low">low</option>
					<option value="medium">medium</option>
					<option value="high">high</option>
					<option value="xhigh">xhigh</option>
				</select>
				<p class="text-[10px] italic text-gray-500 dark:text-gray-400 mt-1 px-1">
					{$i18n.t('Empty inherits the admin default.')}
				</p>
			</div>

			<div>
				<label
					for="subagent-settings-tier"
					class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1 px-1"
				>
					{$i18n.t('Service tier')}
				</label>
				<select
					id="subagent-settings-tier"
					bind:value={subagentServiceTier}
					class="w-full rounded-lg py-1.5 px-3 text-sm bg-gray-50 dark:bg-gray-900 dark:text-gray-100 outline-hidden border-hairline border-gray-200 dark:border-gray-700"
				>
					<option value="">{$i18n.t('default (admin)')}</option>
					{#each allowedServiceTiers as tier}
						<option value={tier}>{tier}</option>
					{/each}
				</select>
				<p class="text-[10px] italic text-gray-500 dark:text-gray-400 mt-1 px-1">
					{$i18n.t('Restricted to the subagent model’s supported tiers.')}
				</p>
			</div>
		</DropdownMenu.Content>
	</div>
</Dropdown>
