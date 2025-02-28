<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import Modal from '$lib/components/common/Modal.svelte';
	import AccessControl from './AccessControl.svelte';

	interface Props {
		show?: boolean;
		accessControl?: any;
		accessRoles?: any;
		onChange?: any;
	}

	let {
		show = $bindable(false),
		accessControl = $bindable(null),
		accessRoles = ['read'],
		onChange = () => {}
	}: Props = $props();
</script>

<Modal size="sm" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-100 px-5 pt-3 pb-1">
			<div class=" text-lg font-medium self-center font-primary">
				{$i18n.t('Access Control')}
			</div>
			<button
				class="self-center"
				onclick={() => {
					show = false;
				}}
			>
				<svg
					class="w-5 h-5"
					fill="currentColor"
					viewBox="0 0 20 20"
					xmlns="http://www.w3.org/2000/svg"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>

		<div class="w-full px-5 pb-4 dark:text-white">
			<AccessControl {accessRoles} {onChange} bind:accessControl />
		</div>
	</div>
</Modal>
