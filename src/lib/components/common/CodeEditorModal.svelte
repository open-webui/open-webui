<script lang="ts">
	import { onMount, getContext } from 'svelte';

	import CodeEditor from './CodeEditor.svelte';
	import Drawer from './Drawer.svelte';

	const i18n = getContext('i18n');

	let {
		show = $bindable(),
		value = $bindable(),
		lang = 'python',
		onChange = () => {},
		onSave = () => {}
	} = $props();

	let boilerplate = ``;

	let codeEditor = $state(null);
	let _content = $state(value);

	$effect(() => {
		if (_content) {
			value = _content;
		}
	});
</script>

<Drawer bind:show>
	<div class="flex h-full flex-col">
		<div
			class=" sticky top-0 z-30 flex justify-between bg-white px-4.5 pt-3 pb-3 dark:bg-gray-900 dark:text-gray-100"
		>
			<div class=" font-primary self-center text-lg font-medium">
				{$i18n.t('Code Editor')}
			</div>
			<button
				class="self-center"
				aria-label="Close"
				onclick={() => {
					show = false;
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

		<div
			class="flex h-full w-full flex-1 flex-col md:flex-row md:space-x-4 dark:text-gray-200 overflow-y-auto"
		>
			<div class=" flex h-full w-full flex-col sm:flex-row sm:justify-center sm:space-x-6">
				<CodeEditor bind:this={codeEditor} {value} {boilerplate} {lang} {onChange} {onSave} />
			</div>
		</div>
	</div>
</Drawer>
