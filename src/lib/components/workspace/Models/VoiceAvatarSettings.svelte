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

<div class="my-3 flex items-center justify-between gap-3">
	<div>
		<div class="text-xs text-gray-500">{$i18n.t('Voice avatar')}</div>
		<div class="text-sm mt-0.5">{$i18n.t(value ? 'Custom avatar' : 'Default orb')}</div>
	</div>
	<button
		type="button"
		{disabled}
		class="text-xs text-gray-500 transition hover:text-gray-700 dark:hover:text-gray-300"
		on:click={open}
	>
		{$i18n.t('Configure')}
	</button>
</div>

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
				class="text-sm px-3 py-2 rounded-lg"
				on:click={() => {
					show = false;
				}}>{$i18n.t('Cancel')}</button
			>
			<button
				type="button"
				disabled={!valid}
				class="text-sm px-4 py-2 rounded-lg bg-black text-white dark:bg-white dark:text-black disabled:opacity-40"
				on:click={apply}>{$i18n.t('Apply')}</button
			>
		</div>
	</div>
</Modal>
