<script lang="ts">
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { AUDIO_PLAYBACKRATE_OPTIONS } from '$lib/constants';
	import { settings } from '$lib/stores';
	import { flyAndScale } from '$lib/utils/transitions';
	import { DropdownMenu } from 'bits-ui';
	import { createEventDispatcher, getContext, onMount } from 'svelte';

	export let audioParams = {
		playbackRate: 1,
		volume: 1
	};

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	
	onMount(async () => {
		audioParams.volume = $settings.audio?.tts?.playbackVolume ?? 1;
		audioParams.playbackRate = $settings.audio?.tts?.playbackRate ?? 1;
	});
	
	$: volumePercentage = Math.round(audioParams.volume * 100);
	
	$: if (audioParams) {
		dispatch('change', audioParams);
	}
</script>

<DropdownMenu.Root typeahead={false} closeOnItemClick={false} closeFocus={false}>
	<DropdownMenu.Trigger>
		<Tooltip content={$i18n.t('Audio Controls')}>
			<slot />
		</Tooltip>
	</DropdownMenu.Trigger>

	<DropdownMenu.Content
		class="w-full max-w-[320px] rounded-xl px-1 py-1.5 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg"
		sideOffset={15}
		alignOffset={0}
		side="bottom"
		align="start"
		transition={flyAndScale}
	>
		<DropdownMenu.Item class="flex px-3 py-1.5 text-sm font-medium">
			<div class="flex w-full justify-between">
				<div class="self-center">{$i18n.t('Speech Playback Speed')}</div>

				<select
					class="w-fit rounded text-xs px-2 pr-8 bg-transparent outline-none text-right cursor-pointer"
					bind:value={audioParams.playbackRate}
				>
					{#each AUDIO_PLAYBACKRATE_OPTIONS as option}
						<option
							class="bg-gray-100 dark:bg-gray-800"
							value={option}
							selected={audioParams.playbackRate === option}>{option}x</option
						>
					{/each}
				</select>
			</div>
		</DropdownMenu.Item>

		<DropdownMenu.Item class="flex px-3 py-2 text-sm font-medium">
			<div class="py-0.5 flex w-full flex-col">
				<div>{$i18n.t('Playback Volume')}</div>

				<div class="flex items-center justify-between">
					<div class="flex-1">
						<input
							bind:value={audioParams.volume}
							id="steps-range"
							type="range"
							min="0"
							max="1"
							step="0.01"
							class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
						/>
					</div>
					<div class="bg-transparent text-center w-14 text-xs">
						{volumePercentage}%
					</div>
				</div>
			</div>
		</DropdownMenu.Item>
	</DropdownMenu.Content>
</DropdownMenu.Root>
