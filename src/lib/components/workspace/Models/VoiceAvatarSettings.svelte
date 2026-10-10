<script lang="ts">
	import { getContext } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import type { AnimationFiles, VoiceAvatarConfig } from '$lib/utils/voice-avatar';
	import VoiceAvatarEditor from './VoiceAvatarEditor.svelte';

	export let value: VoiceAvatarConfig | null = null;
	export let file: File | null = null;
	export let disabled = false;
	export let animationFiles: AnimationFiles = {};
	let draftAnimationFiles: AnimationFiles = {};
	const i18n = getContext<any>('i18n');
	let show = false;
	let draft: VoiceAvatarConfig | null = null;
	let draftFile: File | null = null;
	let valid = true;
	const open = () => {
		draft = value ? structuredClone(value) : null;
		draftFile = file;
		draftAnimationFiles = { ...animationFiles };
		valid = !file;
		show = true;
	};
	const apply = () => {
		if (!valid) return;
		value = draft;
		file = draftFile;
		animationFiles = draftAnimationFiles;
		show = false;
	};
</script>

<button
	type="button"
	{disabled}
	on:click={open}
	class="grid min-h-8 w-full grid-cols-[7rem_minmax(0,1fr)_auto] items-center gap-2 rounded-md px-1 py-1 text-left text-xs font-normal disabled:opacity-50 sm:grid-cols-[8rem_minmax(0,1fr)_auto]"
>
	<span class="text-gray-600 dark:text-gray-400">{$i18n.t('Voice avatar')}</span>
	<span class="truncate text-gray-900 dark:text-gray-100"
		>{value ? $i18n.t('Custom avatar') : $i18n.t('Default orb')}</span
	>
	<span class="text-gray-500 dark:text-gray-400">{$i18n.t('Configure')}</span>
</button>

<Modal bind:show size="sm">
	<div class="p-5 text-gray-900 dark:text-gray-100">
		<div class="flex items-center justify-between gap-3">
			<h2 class="text-base font-medium">{$i18n.t('Avatar setup')}</h2>
			<button
				type="button"
				class="p-1 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-850"
				aria-label={$i18n.t('Close avatar setup')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark className="size-4" />
			</button>
		</div>
		{#if show}
			<div class="max-h-[70dvh] overflow-y-auto scrollbar-hidden">
				<VoiceAvatarEditor
					bind:value={draft}
					bind:file={draftFile}
					bind:animationFiles={draftAnimationFiles}
					bind:valid
				/>
			</div>
		{/if}
		<div class="flex justify-end gap-2 mt-5">
			<button
				type="button"
				class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg px-2.5 text-xs font-normal transition disabled:opacity-60 hover:bg-gray-100 dark:hover:bg-gray-850"
				on:click={() => {
					show = false;
				}}>{$i18n.t('Cancel')}</button
			>
			<button
				type="button"
				disabled={!valid}
				class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-gray-900 px-2.5 text-xs font-normal text-white transition hover:bg-black disabled:opacity-60 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white"
				on:click={apply}>{$i18n.t('Apply')}</button
			>
		</div>
	</div>
</Modal>
