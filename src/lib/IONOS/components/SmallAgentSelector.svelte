<script lang="ts">
	import type { Tag } from '$lib/apis';
	import { models, settings } from '$lib/stores';
	import { updateUserSettings } from '$lib/apis/users';
	import AgentIcon from './AgentIcon.svelte';
	import Button, { ButtonType } from '$lib/IONOS/components/common/Button.svelte'

	export let selectedModels = [''];

	// Custom models obey have the convention of using only characters
	// This excludes stock models.
	// This can later be changed to testing for a marker tag in info.meta.tags
	const onlyCustomModels = ({ id }: { id: string }) => /^[a-z]+$/.test(id);

	/**
	 * Reduce tags to a string where the tag icon:<name> becomes <name>
	 */
	const tagsToIconName = (iconNameSoFar: string, tagObject: Tag): string => {
		if (iconNameSoFar) {
			return iconNameSoFar;
		}
		return tagObject?.name?.split('icon:')?.[1] ?? '';
	};

	$: modelsUi = $models
		.filter(onlyCustomModels)
		.map((model) => ({
			id: model.id,
			iconName: model?.info?.meta?.tags?.reduce(tagsToIconName, ''),
			modelDisplayName: model.name ?? '',
		}));

	const save = async () => {
		settings.set({ ...$settings, models: selectedModels });
		await updateUserSettings(localStorage.token, { ui: $settings });
	}

	const select = (id: string) => {
		selectedModels = [id];
		save();
	}
</script>

<div class="flex flex-row items-start gap-3">
	{#each modelsUi as { id, modelDisplayName, iconName }}
		<Button
			name={id}
			on:click={() => select(id)}
			className="px-4 py-1 font-semibold text-sm font-sans flex flex-row items-center"
			type={ButtonType.secondary}
			pressable={true}
			pressed={id === selectedModels[0]}
		>
			<AgentIcon {iconName} />
			<span class="ml-1 text-nowrap">{modelDisplayName}</span>
		</Button>
	{/each}
</div>
