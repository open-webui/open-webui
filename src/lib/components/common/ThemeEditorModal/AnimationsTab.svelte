<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import type { Theme } from '$lib/types';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import CodeBlock from '$lib/components/chat/Messages/CodeBlock.svelte';

	export let themeCopy: Theme;
	export let animationScriptText: string;
	export let tsParticleConfigText: string;

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	const handleAnimationScriptInput = (e) => {
		animationScriptText = e.detail;
		themeCopy.animationScript = animationScriptText;
		dispatch('update', { ...themeCopy });
	};

	const handleTsParticleConfigInput = (e) => {
		tsParticleConfigText = e.detail;
		try {
			themeCopy.tsparticlesConfig = JSON.parse(tsParticleConfigText);
			dispatch('update', { ...themeCopy });
		} catch (error) {
			if (tsParticleConfigText.trim() === '') {
				themeCopy.tsparticlesConfig = undefined;
				dispatch('update', { ...themeCopy });
			}
		}
	};
</script>

<div class="space-y-4">
	<div>
		<div class="flex items-center gap-2">
			<Switch
				bind:state={themeCopy.toggles.animationScript}
				on:change={() => dispatch('update', { ...themeCopy })}
			/>
			<Tooltip
				content="Add custom Javascript to create animations. This is for advanced themes that use canvas or other dynamic elements."
			>
				<label
					for="theme-animation-script"
					class="block text-sm font-medium text-gray-700 dark:text-gray-300"
					>{$i18n.t('Animation Script')}</label
				>
			</Tooltip>
		</div>
		{#if themeCopy.toggles.animationScript}
			{#key 'animation-script'}
				<div class="mt-1 rounded-lg overflow-hidden">
					<CodeBlock
						id="theme-animation-script-editor"
						code={animationScriptText}
						lang={'javascript'}
						edit={true}
						on:change={handleAnimationScriptInput}
					/>
				</div>
			{/key}
		{/if}
	</div>
	<div>
		<div class="flex items-center gap-2">
			<Switch
				bind:state={themeCopy.toggles.tsParticles}
				on:change={() => dispatch('update', { ...themeCopy })}
			/>
			<Tooltip content="Configuration object for tsParticles animations.">
				<label
					for="theme-tsparticle-config"
					class="block text-sm font-medium text-gray-700 dark:text-gray-300"
					>{$i18n.t('tsParticles Config')}</label
				>
			</Tooltip>
		</div>
		{#if themeCopy.toggles.tsParticles}
			{#key 'tsparticles-config'}
				<div class="mt-1 rounded-lg overflow-hidden">
					<CodeBlock
						id="theme-tsparticle-config-editor"
						code={tsParticleConfigText}
						lang={'json'}
						edit={true}
						on:change={handleTsParticleConfigInput}
					/>
				</div>
			{/key}
		{/if}
	</div>
</div>
