<script lang="ts">
	import { onMount } from 'svelte';

	export let editor: any = null;
	export let enabled: boolean = true;

	let showPii = false;
	let attachedEditor: any = null;

	const isValidSelection = () => {
		if (!editor) return false;
		const { from, to } = editor.state?.selection || { from: 0, to: 0 };
		const len = to - from;
		return len >= 2 && len <= 50;
	};

	const updateVisibility = () => {
		showPii = enabled && isValidSelection();
	};

	function handleEditorEvent() {
		updateVisibility();
	}

	function attach(e: any) {
		if (!e || attachedEditor === e) return;
		e?.on?.('selectionUpdate', handleEditorEvent);
		e?.on?.('transaction', handleEditorEvent);
		e?.on?.('update', handleEditorEvent);
		attachedEditor = e;
		updateVisibility();
	}

	function detach() {
		if (!attachedEditor) return;
		attachedEditor?.off?.('selectionUpdate', handleEditorEvent);
		attachedEditor?.off?.('transaction', handleEditorEvent);
		attachedEditor?.off?.('update', handleEditorEvent);
		attachedEditor = null;
	}

	onMount(() => {
		// Initial attach if editor is ready on mount
		if (enabled && editor) attach(editor);
		// Cleanup on unmount
		return () => {
			detach();
		};
	});

	// React to editor or enabled changes (covers HMR + dynamic hosts)
	$: {
		if (enabled && editor) {
			if (attachedEditor !== editor) {
				detach();
				attach(editor);
			} else {
				// Even if same editor, recompute when enabled toggles
				updateVisibility();
			}
		} else {
			// Disabled or no editor → ensure cleanup and hide
			if (attachedEditor) detach();
			showPii = false;
		}
	}

	const addWordMask = () => {
		if (!isValidSelection()) return;
		// Use the new addWordMaskModifier command that finds complete words in selection
		editor?.commands?.addWordMaskModifier?.();
	};
</script>

{#if enabled && editor && showPii}
	<div
		class="flex gap-0.5 p-0.5 rounded-lg shadow-lg bg-white text-gray-800 dark:text-white dark:bg-gray-800 min-w-fit"
	>
		<button
			type="button"
			class="hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg p-1.5 transition-all text-xs font-medium flex items-center gap-1"
			on:click={addWordMask}
			title="PII Modifier: Mask complete words in selection"
		>
			🛡️ Mask Words
		</button>
	</div>
{/if}

<style>
	/* No custom styles; rely on Tailwind utility classes from project */
</style>
