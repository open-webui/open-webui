<script lang="ts">
	import { resolveLocalizedResource } from '$lib/utils/localizedContent';
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import { skills } from '$lib/stores';

	import Modal from '../common/Modal.svelte';
	import Collapsible from '../common/Collapsible.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let terminalSkills: Writable<any[]>;

	export let show = false;
	export let selectedSkillIds = [];

	let selectedSkills = [];

	$: selectedSkills = [...($skills ?? []), ...($terminalSkills ?? [])].filter((skill) =>
		selectedSkillIds.includes(skill.id)
	);

	const i18n = getContext('i18n');
</script>

<Modal ariaLabel={$i18n.t('Available Skills')} bind:show size="md">
	<div>
		<div class=" flex justify-between dark:text-base-300 px-4 pt-3 pb-1">
			<div class=" text-sm font-medium self-center">{$i18n.t('Available Skills')}</div>
			<button
				class="self-center rounded-lg py-1 text-base-500 transition hover:text-base-700 dark:text-base-400 dark:hover:text-base-200 px-0"
				aria-label={$i18n.t('Close')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-4'} />
			</button>
		</div>

		{#if selectedSkills.length > 0}
			<div class=" flex justify-between dark:text-base-300 px-4 pb-1">
				<div class="text-xs text-base-500 self-center">{$i18n.t('Skills')}</div>
			</div>

			<div class="px-4 pb-4 w-full flex flex-col justify-center">
				<div class=" text-sm dark:text-base-300 mb-1">
					{#each selectedSkills as skill}
						<Collapsible buttonClassName="w-full mb-0.5">
							<div class="truncate">
								<div class="text-sm font-normal dark:text-base-100 text-base-800 truncate">
									{resolveLocalizedResource(skill, $i18n.language)}
								</div>

								{#if resolveLocalizedResource(skill, $i18n.language, 'description')}
									<div class="text-xs text-base-500">
										{resolveLocalizedResource(skill, $i18n.language, 'description')}
									</div>
								{/if}
								{#if skill.source === 'terminal'}
									<div class="text-xs text-base-500">{$i18n.t('Machine')}</div>
								{/if}
							</div>
						</Collapsible>
					{/each}
				</div>
			</div>
		{/if}
	</div>
</Modal>
