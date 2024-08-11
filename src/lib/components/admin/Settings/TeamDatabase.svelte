<script lang="ts">
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { downloadMembersList } from '$lib/apis/teams';
	import { onMount, getContext } from 'svelte';
	import { config, user } from '$lib/stores';
	import { toast } from 'svelte-sonner';
	import { getAllUserChats } from '$lib/apis/chats';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	onMount(async () => {
		// permissions = await getUserPermissions(localStorage.token);
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={async () => {
		saveHandler();
	}}
>
	<div class=" space-y-3 overflow-y-scroll scrollbar-hidden h-full">
		<div>
			<div class=" mb-2 text-sm font-medium">{$i18n.t('Teams')}</div>

			{#if $config?.features.enable_admin_export ?? true}
				<div class="  flex w-full justify-between">
					<button
						class=" flex rounded-md py-1.5 px-3 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
						type="button"
						on:click={() => {
							downloadMembersList(localStorage.token).catch((error) => {
								toast.error(error);
							});
						}}
					>
						<div class=" self-center mr-3">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								class="w-4 h-4"
							>
								<path d="M2 3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3Z" />
								<path
									fill-rule="evenodd"
									d="M13 6H3v6a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V6ZM8.75 7.75a.75.75 0 0 0-1.5 0v2.69L6.03 9.22a.75.75 0 0 0-1.06 1.06l2.5 2.5a.75.75 0 0 0 1.06 0l2.5-2.5a.75.75 0 1 0-1.06-1.06l-1.22 1.22V7.75Z"
									clip-rule="evenodd"
								/>
							</svg>
						</div>
						<div class=" self-center text-sm font-medium">{$i18n.t('Download Members')}</div>
					</button>
				</div>
			{/if}

			<hr class=" dark:border-gray-850 my-1" />

			<div class="  flex w-full justify-between"></div>
			<!-- <div class=" self-center text-xs font-medium">{$i18n.t('Allow Chat Deletion')}</div> -->
		</div>
	</div>
</form>
