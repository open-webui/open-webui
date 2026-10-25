<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as I18n } from 'i18next';
	import {
		CONTROL_GROUPS,
		CONTROL_LABELS,
		type ControlId,
		type Visibility
	} from '$lib/utils/ui-visibility';
	import ModelSettingsSection from '$lib/components/workspace/Models/ModelSettingsSection.svelte';
	import ModelSettingToggle from '$lib/components/workspace/Models/ModelSettingToggle.svelte';
	import AdminSettingSection from '../AdminSettingSection.svelte';
	import AdminSettingRow from '../AdminSettingRow.svelte';

	const i18n: Writable<I18n> = getContext('i18n');
	export let visibility: Visibility = {};
	let expanded = false;
	const controls = Object.keys(CONTROL_LABELS) as ControlId[];

	const setVisible = (id: ControlId, visible: boolean) => {
		visibility = { ...visibility };
		if (visible) delete visibility[id];
		else visibility[id] = false;
	};
</script>

<AdminSettingSection title={$i18n.t('Visibility')} first>
	<AdminSettingRow
		let:labelId
		label={$i18n.t('settings.admin.interface.visibility.title')}
		description={$i18n.t('settings.admin.interface.visibility.description')}
	>
		<button
			id={`${labelId}-control`}
			type="button"
			class="focus-ring text-xs text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
			aria-expanded={expanded}
			aria-controls="interface-visible-controls"
			on:click={() => (expanded = !expanded)}
		>
			{expanded ? $i18n.t('Hide') : $i18n.t('Show')}
		</button>
	</AdminSettingRow>
	<div id="interface-visible-controls" hidden={!expanded}>
		<div class="space-y-0.5">
			{#each CONTROL_GROUPS as [prefix, label]}
				<ModelSettingsSection label={$i18n.t(label)}>
					<div class="grid grid-cols-1 gap-x-6 sm:grid-cols-2 lg:grid-cols-3">
						{#each controls.filter((id) => id.startsWith(prefix)) as id}
							<ModelSettingToggle
								label={$i18n.t(CONTROL_LABELS[id])}
								checked={visibility[id] !== false}
								on:change={(event) => setVisible(id, event.detail)}
							/>
						{/each}
					</div>
				</ModelSettingsSection>
			{/each}
		</div>
	</div>
</AdminSettingSection>
