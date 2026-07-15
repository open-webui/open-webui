<script lang="ts">
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { downloadDatabase } from '$lib/apis/utils';
	import { getContext } from 'svelte';
	import { config } from '$lib/stores';
	import { toast } from 'svelte-sonner';
	import { getAllUserChats } from '$lib/apis/chats';
	import { getAllUsers } from '$lib/apis/users';
	import { exportConfig, importConfig } from '$lib/apis/configs';

	const i18n: any = getContext('i18n');

	export let saveHandler: Function;

	const actionButtonClass =
		'px-0.5 text-xs text-gray-500 underline-offset-2 transition-colors hover:text-gray-900 hover:underline dark:text-gray-500 dark:hover:text-white';

	const exportAllUserChats = async () => {
		let blob = new Blob([JSON.stringify(await getAllUserChats(localStorage.token))], {
			type: 'application/json'
		});
		saveAs(blob, `all-chats-export-${Date.now()}.json`);
	};

	const exportUsers = async () => {
		const users = await getAllUsers(localStorage.token);

		const headers = ['id', 'name', 'email', 'role'];

		const csv = [
			headers.join(','),
			...users.users.map((user) => {
				return headers
					.map((header) => {
						if (user[header] === null || user[header] === undefined) {
							return '';
						}
						return `"${String(user[header]).replace(/"/g, '""')}"`;
					})
					.join(',');
			})
		].join('\n');

		const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
		saveAs(blob, 'users.csv');
	};
</script>

<div class="flex flex-col h-full justify-between text-sm">
	<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-4">{$i18n.t('Database')}</h2>

	<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5">
		<input
			id="config-json-input"
			hidden
			type="file"
			accept=".json"
			on:change={(e) => {
				const file = e.target.files[0];
				const reader = new FileReader();

				reader.onload = async (e) => {
					const res = await importConfig(localStorage.token, JSON.parse(e.target.result)).catch(
						(error) => {
							toast.error(`${error}`);
						}
					);

					if (res) {
						toast.success($i18n.t('Config imported successfully'));
					}
					e.target.value = null;
				};

				reader.readAsText(file);
			}}
		/>

		<div class="flex w-full flex-col gap-2.5">
			<div class="flex flex-wrap items-center gap-x-1.5 gap-y-1">
				<span class="mr-1 text-xs text-gray-600 dark:text-gray-400">{$i18n.t('Config')}</span>
				<button
					class={actionButtonClass}
					on:click={() => {
						document.getElementById('config-json-input')?.click();
					}}
					type="button"
				>
					{$i18n.t('Import')}
				</button>

				<button
					class={actionButtonClass}
					on:click={async () => {
						const config = await exportConfig(localStorage.token);
						const blob = new Blob([JSON.stringify(config)], {
							type: 'application/json'
						});
						saveAs(blob, `config-${Date.now()}.json`);
					}}
					type="button"
				>
					{$i18n.t('Export')}
				</button>
			</div>

			{#if $config?.features.enable_admin_export ?? true}
				<div class="flex flex-wrap items-center gap-x-1.5 gap-y-1">
					<span class="mr-1 text-xs text-gray-600 dark:text-gray-400">{$i18n.t('Export')}</span>
					<button
						class={actionButtonClass}
						on:click={() => {
							downloadDatabase(localStorage.token).catch((error) => {
								toast.error(`${error}`);
							});
						}}
						type="button"
					>
						{$i18n.t('Database')}
					</button>

					<button class={actionButtonClass} on:click={exportAllUserChats} type="button">
						{$i18n.t('All chats')}
					</button>

					<button class={actionButtonClass} on:click={exportUsers} type="button">
						{$i18n.t('Users')}
					</button>
				</div>
			{/if}
		</div>
	</div>
</div>
