<script lang="ts">
	import { getContext } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import FileNav from '$lib/components/chat/FileNav.svelte';
	import type { TerminalTarget } from '$lib/apis/terminal';

	const i18n = getContext<any>('i18n');

	/** Browses one machine's files: the terminal, plus the chat or model it belongs to. */
	export let target: TerminalTarget;
	export let label: string;
	export let onClose: () => void;
</script>

<Modal size="lg" ariaLabel={$i18n.t('Files on {{name}}', { name: label })} onRequestClose={onClose}>
	<div class="p-4 text-gray-900 dark:text-gray-100">
		<div class="mb-3 flex items-center justify-between gap-2">
			<h2 class="min-w-0 truncate text-sm font-medium" title={label}>{label}</h2>
			<button
				type="button"
				aria-label={$i18n.t('Close')}
				class="shrink-0 text-gray-500 hover:text-gray-900 dark:hover:text-gray-100"
				on:click={onClose}><XMark className="size-4" /></button
			>
		</div>
		<div class="h-[70dvh] min-h-0">
			<FileNav {target} manageFileRequests={false} showTerminalDock={false} />
		</div>
	</div>
</Modal>
