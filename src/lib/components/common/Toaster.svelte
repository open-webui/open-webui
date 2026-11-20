<script lang="ts">
	import { Toaster } from 'svelte-sonner';

	import CheckCircle from '$lib/components/icons/CheckCircle.svelte';
	import ExclamationCircle from '$lib/components/icons/ExclamationCircle.svelte';
	import ExclamationTriangle from '$lib/components/icons/ExclamationTriangle.svelte';
	import Info from '$lib/components/icons/Info.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	export let position:
		| 'top-left'
		| 'top-right'
		| 'bottom-left'
		| 'bottom-right'
		| 'top-center'
		| 'bottom-center' = 'top-right';
	export let closeButton = true;

	// svelte-sonner's stylesheet is unlayered, so it beats Tailwind's utilities unless they are important.
	const button =
		'-mt-0.5 h-6 shrink-0 cursor-pointer rounded-lg px-2 text-xs font-medium text-gray-800 dark:text-gray-100 outline-none focus-visible:ring-1! focus-visible:ring-gray-300 dark:focus-visible:ring-gray-600';
</script>

<Toaster
	{position}
	{closeButton}
	toastOptions={{
		unstyled: true,
		classes: {
			toast:
				'group/toast flex w-full items-start gap-2.5 rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-850 p-3 font-primary text-[0.8125rem] text-gray-800 dark:text-gray-100 shadow-lg shadow-black/5 dark:shadow-black/30 outline-none focus-visible:ring-2 focus-visible:ring-gray-200 dark:focus-visible:ring-gray-700 has-[>[data-toast-custom]]:p-0 [&_[data-content]]:flex [&_[data-content]]:min-w-0 [&_[data-content]]:flex-1 [&_[data-content]]:flex-col [&_[data-content]]:gap-0.5 [&_[data-icon]]:flex [&_[data-icon]]:h-[1lh]! [&_[data-icon]]:shrink-0 [&_[data-icon]]:items-center [&_[data-icon]]:m-0! [&_[data-icon]_svg]:m-0!',
			title: 'font-medium text-gray-900 dark:text-gray-50',
			description: 'text-xs text-gray-500 dark:text-gray-400',
			actionButton: `${button} bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700`,
			cancelButton: `${button} bg-transparent! hover:bg-gray-100! dark:hover:bg-gray-800!`,
			closeButton:
				'static! order-last -mr-0.5 size-5! shrink-0 transform-none! rounded-md! border-0! bg-transparent! text-gray-400! outline-none transition hover:bg-gray-100! hover:text-gray-700! dark:text-gray-500! dark:hover:bg-gray-800! dark:hover:text-gray-200! focus-visible:ring-1! focus-visible:ring-gray-300 dark:focus-visible:ring-gray-600'
		}
	}}
	{...$$restProps}
>
	<CheckCircle slot="success-icon" className="size-4 text-green-500" strokeWidth="2" />
	<ExclamationCircle slot="error-icon" className="size-4 text-red-500" strokeWidth="2" />
	<ExclamationTriangle slot="warning-icon" className="size-4 text-amber-500" strokeWidth="2" />
	<Info slot="info-icon" className="size-4 text-blue-500" strokeWidth="2" />
	<span
		slot="loading-icon"
		class="hidden text-gray-400 dark:text-gray-500 group-data-[type=loading]/toast:flex"
	>
		<Spinner className="size-4" />
	</span>
</Toaster>
