<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher } from 'svelte';
	import { onMount, getContext } from 'svelte';
	import { addRole } from '$lib/apis/roles';

	import { WEBUI_BASE_URL } from '$lib/constants';

	import Modal from '$lib/components/common/Modal.svelte';

	const i18n = getContext('i18n');

</script>

<div>
	<div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-2">
		<div class=" text-lg font-medium self-center">{$i18n.t('Add Role')}</div>
		<button
			class="self-center"
			on:click={() => {
				show = false;
			}}
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="w-5 h-5"
			>
				<path
					d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
				/>
			</svg>
		</button>
	</div>

	<div class="flex flex-col md:flex-row w-full px-4 pb-3 md:space-x-4 dark:text-gray-200">
		<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
			<form class="flex flex-col w-full">
				<div class="flex flex-col w-full mt-1">
					<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Name')}</div>

					<div class="flex-1">
						<input
							class="w-full text-sm bg-transparent disabled:text-gray-500 dark:disabled:text-gray-500 outline-hidden"
							type="text"
							placeholder={$i18n.t('Role name, should be lower case and without spaces')}
							autocomplete="off"
							required
						/>
					</div>
				</div>
			</form>
		</div>
	</div>
</div>
