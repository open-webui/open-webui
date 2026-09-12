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
	import AdminSettingRow from './AdminSettingRow.svelte';
	import AdminSettingSection from './AdminSettingSection.svelte';

	const i18n: any = getContext('i18n');

	export let saveHandler: Function;

	let configImportInputElement: HTMLInputElement;
	const actionButtonClass =
		'text-xs text-gray-500 transition-colors hover:text-gray-900 dark:text-gray-500 dark:hover:text-white';

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
			bind:this={configImportInputElement}
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

		<AdminSettingSection title={$i18n.t('Config')} first>
			<AdminSettingRow
				label={$i18n.t('Import Config')}
				description={$i18n.t('Import admin configuration from a JSON export file.')}
			>
				<button
					class={actionButtonClass}
					on:click={() => {
						configImportInputElement.click();
					}}
					type="button"
				>
					{$i18n.t('Import')}
				</button>
			</AdminSettingRow>

			<AdminSettingRow
				label={$i18n.t('Export Config')}
				description={$i18n.t('Download the current admin configuration as JSON.')}
			>
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
			</AdminSettingRow>
		</AdminSettingSection>

		{#if $config?.features.enable_admin_export ?? true}
			<AdminSettingSection title={$i18n.t('Export')}>
				<AdminSettingRow
					label={$i18n.t('Database')}
					description={$i18n.t('Download the application database when supported.')}
				>
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
				</AdminSettingRow>

				<AdminSettingRow
					label={$i18n.t('All Chats')}
					description={$i18n.t("Download every user's chat history as JSON.")}
				>
					<button class={actionButtonClass} on:click={exportAllUserChats} type="button">
						{$i18n.t('Export')}
					</button>
				</AdminSettingRow>

				<AdminSettingRow
					label={$i18n.t('Users')}
					description={$i18n.t('Download all users as CSV.')}
				>
					<button class={actionButtonClass} on:click={exportUsers} type="button">
						{$i18n.t('Export')}
					</button>
				</AdminSettingRow>
			</AdminSettingSection>
		{/if}
	</div>
</div>
