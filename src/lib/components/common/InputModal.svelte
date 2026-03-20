<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { settings } from '$lib/stores';

	import Drawer from './Drawer.svelte';
	import RichTextInput from './RichTextInput.svelte';

	const i18n = getContext('i18n');

	export let id = 'input-modal';

	export let show = false;
	export let value = null;
	export let inputContent = null;

	export let autocomplete = false;
	export let generateAutoCompletion = null;

	export let onChange = () => {};
	export let onClose = () => {};

	let inputElement;
</script>

<Drawer bind:show>
	<div class="flex h-full min-h-screen flex-col">
		<div
			class=" sticky top-0 z-30 flex justify-between bg-white px-4.5 pt-3 pb-3 dark:bg-gray-900 dark:text-gray-100"
		>
			<div class=" font-primary self-center text-lg">
				{$i18n.t('Input')}
			</div>
			<button
				class="self-center"
				aria-label="Close"
				onclick={() => {
					show = false;
					onClose();
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="h-5 w-5"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>

		<div class="flex w-full px-4 dark:text-gray-200 min-h-full flex-1">
			<div class="flex-1 w-full min-h-full">
				<RichTextInput
					bind:this={inputElement}
					{id}
					onChange={(content) => {
						value = content.md;
						inputContent = content;

						onChange(content);
					}}
					json={true}
					value={inputContent?.json}
					html={inputContent?.html}
					richText={$settings?.richTextInput ?? true}
					messageInput={true}
					showFormattingToolbar={$settings?.showFormattingToolbar ?? false}
					floatingMenuPlacement={'top-start'}
					insertPromptAsRichText={$settings?.insertPromptAsRichText ?? false}
					{autocomplete}
					{generateAutoCompletion}
				/>
			</div>
		</div>
	</div>
</Drawer>
