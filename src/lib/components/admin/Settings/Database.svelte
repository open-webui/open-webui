<script lang="ts">
	// @ts-ignore
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { downloadDatabase } from '$lib/apis/utils';
	import { onMount, getContext } from 'svelte';
	import { config, user } from '$lib/stores';
	import { toast } from 'svelte-sonner';
	import { getAllUserChats } from '$lib/apis/chats';
	import { getAllUsers } from '$lib/apis/users';
	import { exportConfig, importConfig } from '$lib/apis/configs';

	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let saveHandler: () => void;

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
			...users.users.map((user: any) => {
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
	<div class="space-y-3 overflow-y-scroll scrollbar-hidden h-full">
		<div class="max-w-5xl mx-auto">
			<div>
				<div class="mb-3">
					<div class="mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('Database')}</div>
					<hr class="border-gray-100/30 dark:border-gray-850/30 my-2" />
				</div>

				<div
					class="bg-gray-50 dark:bg-gray-850 rounded-lg p-5 border border-gray-100 dark:border-gray-800"
				>
					<input
						id="config-json-input"
						hidden
						type="file"
						accept=".json"
						on:change={(e) => {
							const target = e.target as HTMLInputElement;
							const file = target.files?.[0];
							if (!file) return;

							const reader = new FileReader();

							reader.onload = async (e) => {
								const result = e.target?.result as string;
								if (!result) return;

								const res = await importConfig(localStorage.token, JSON.parse(result)).catch(
									(error) => {
										toast.error(`${error}`);
									}
								);

								if (res) {
									toast.success($i18n.t('Config imported successfully'));
								}
								target.value = '';
							};

							reader.readAsText(file);
						}}
					/>

					<div class="space-y-2">
						<div class="text-xs font-medium text-gray-500">{$i18n.t('Config')}</div>
						<button
							type="button"
							class="flex rounded-md py-2 px-3 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
							on:click={async () => {
								const input = document.getElementById('config-json-input');
								if (input) input.click();
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
							<div class=" self-center text-sm font-medium">
								{$i18n.t('Import Config from JSON File')}
							</div>
						</button>

						<button
							type="button"
							class="flex rounded-md py-2 px-3 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
							on:click={async () => {
								const config = await exportConfig(localStorage.token);
								const blob = new Blob([JSON.stringify(config)], {
									type: 'application/json'
								});
								saveAs(blob, `config-${Date.now()}.json`);
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
							<div class=" self-center text-sm font-medium">
								{$i18n.t('Export Config to JSON File')}
							</div>
						</button>
					</div>

					<hr class="border-gray-100 dark:border-gray-800 my-3" />

					{#if $config?.features.enable_admin_export ?? true}
						<div class="space-y-2">
							<div class="text-xs font-medium text-gray-500">{$i18n.t('Exports')}</div>
							<div class="flex w-full justify-between">
								<!-- <div class=" self-center text-xs font-medium">{$i18n.t('Allow Chat Deletion')}</div> -->

								<button
									class="flex rounded-md py-1.5 px-3 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
									type="button"
									on:click={() => {
										// exportAllUserChats();

										downloadDatabase(localStorage.token).catch((error) => {
											toast.error(`${error}`);
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
											<path
												d="M2 3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3Z"
											/>
											<path
												fill-rule="evenodd"
												d="M13 6H3v6a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V6ZM8.75 7.75a.75.75 0 0 0-1.5 0v2.69L6.03 9.22a.75.75 0 0 0-1.06 1.06l2.5 2.5a.75.75 0 0 0 1.06 0l2.5-2.5a.75.75 0 1 0-1.06-1.06l-1.22 1.22V7.75Z"
												clip-rule="evenodd"
											/>
										</svg>
									</div>
									<div class=" self-center text-sm font-medium">{$i18n.t('Download Database')}</div>
								</button>
							</div>

							<button
								class="flex rounded-md py-2 px-3 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
								on:click={() => {
									exportAllUserChats();
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
								<div class=" self-center text-sm font-medium">
									{$i18n.t('Export All Chats (All Users)')}
								</div>
							</button>

							<button
								class="flex rounded-md py-2 px-3 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
								on:click={() => {
									exportUsers();
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
								<div class=" self-center text-sm font-medium">
									{$i18n.t('Export Users')}
								</div>
							</button>
						</div>
					{/if}
				</div>
			</div>
		</div>
	</div>
</form>
