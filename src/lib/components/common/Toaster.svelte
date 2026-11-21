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
		'-mt-0.5 h-6 shrink-0 cursor-pointer rounded-lg px-2 text-xs font-medium text-base-800 dark:text-base-100 outline-none focus-visible:ring-1! focus-visible:ring-base-300 dark:focus-visible:ring-base-600';
</script>

<Toaster
	{position}
	{closeButton}
	toastOptions={{
		unstyled: true,
		classes: {
			toast:
				'group/toast flex w-full items-start gap-2.5 rounded-2xl border border-base-100 dark:border-base-800 bg-base-0 dark:bg-base-850 p-3 font-primary text-[0.8125rem] text-base-800 dark:text-base-100 shadow-lg shadow-black/5 dark:shadow-black/30 outline-none focus-visible:ring-2 focus-visible:ring-base-200 dark:focus-visible:ring-base-700 has-[>[data-toast-custom]]:p-0 [&_[data-content]]:flex [&_[data-content]]:min-w-0 [&_[data-content]]:flex-1 [&_[data-content]]:flex-col [&_[data-content]]:gap-0.5 [&_[data-icon]]:flex [&_[data-icon]]:h-[1lh]! [&_[data-icon]]:shrink-0 [&_[data-icon]]:items-center [&_[data-icon]]:m-0! [&_[data-icon]_svg]:m-0!',
			title: 'font-medium text-base-900 dark:text-base-50',
			description: 'text-xs text-base-500 dark:text-base-400',
			actionButton: `${button} bg-base-100 hover:bg-base-200 dark:bg-base-800 dark:hover:bg-base-700`,
			cancelButton: `${button} bg-transparent! hover:bg-base-100! dark:hover:bg-base-800!`,
			closeButton:
				'static! order-last -mr-0.5 size-5! shrink-0 transform-none! rounded-md! border-0! bg-transparent! text-base-400! outline-none transition hover:bg-base-100! hover:text-base-700! dark:text-base-500! dark:hover:bg-base-800! dark:hover:text-base-200! focus-visible:ring-1! focus-visible:ring-base-300 dark:focus-visible:ring-base-600'
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
		class="hidden text-base-400 dark:text-base-500 group-data-[type=loading]/toast:flex"
	>
		<Spinner className="size-4" />
	</span>
</Toaster>
