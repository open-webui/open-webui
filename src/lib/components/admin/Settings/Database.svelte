<script lang="ts">
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { downloadDatabase } from '$lib/apis/utils';
	import { onMount, getContext } from 'svelte';
	import { config, user } from '$lib/stores';
	import { toast } from 'svelte-sonner';
	import { getAllUserChats } from '$lib/apis/chats';
	import { getAllUsers } from '$lib/apis/users';
	import { exportConfig, importConfig } from '$lib/apis/configs';
	import { clearGeminiCache } from '$lib/apis/gemini-rag';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let clearingCache = false;

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
			<div class=" mb-2 text-sm font-medium">{$i18n.t('Database')}</div>

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

			<button
				type="button"
				class=" flex rounded-md py-2 px-3 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={async () => {
					document.getElementById('config-json-input').click();
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
				class=" flex rounded-md py-2 px-3 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
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

			<hr class="border-gray-50 dark:border-gray-850 my-1" />

			{#if $config?.features.enable_admin_export ?? true}
				<div class="  flex w-full justify-between">
					<!-- <div class=" self-center text-xs font-medium">{$i18n.t('Allow Chat Deletion')}</div> -->

					<button
						class=" flex rounded-md py-1.5 px-3 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
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
								<path d="M2 3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3Z" />
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
					class=" flex rounded-md py-2 px-3 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
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
					class=" flex rounded-md py-2 px-3 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
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

				<hr class="border-gray-50 dark:border-gray-850 my-1" />

				<!-- Gemini Cache Clear Button -->
				<button
					type="button"
					class=" flex rounded-md py-2 px-3 w-full hover:bg-red-100 dark:hover:bg-red-900/20 transition disabled:opacity-50"
					disabled={clearingCache}
					on:click={async () => {
						if (!confirm($i18n.t('정말로 Gemini Cache를 초기화하시겠습니까? 이 작업은 되돌릴 수 없습니다.'))) {
							return;
						}

						clearingCache = true;
						try {
							await clearGeminiCache(localStorage.token);
							toast.success($i18n.t('Gemini Cache가 성공적으로 초기화되었습니다.'));
						} catch (error) {
							console.error('Failed to clear Gemini cache:', error);
							toast.error($i18n.t('Gemini Cache 초기화에 실패했습니다.'));
						}
						clearingCache = false;
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
								fill-rule="evenodd"
								d="M5 3.25V4H2.75a.75.75 0 0 0 0 1.5h.3l.815 8.15A1.5 1.5 0 0 0 5.357 15h5.285a1.5 1.5 0 0 0 1.493-1.35l.815-8.15h.3a.75.75 0 0 0 0-1.5H11v-.75A2.25 2.25 0 0 0 8.75 1h-1.5A2.25 2.25 0 0 0 5 3.25Zm2.25-.75a.75.75 0 0 0-.75.75V4h3v-.75a.75.75 0 0 0-.75-.75h-1.5ZM6.05 6a.75.75 0 0 1 .787.713l.275 5.5a.75.75 0 0 1-1.498.075l-.275-5.5A.75.75 0 0 1 6.05 6Zm3.9 0a.75.75 0 0 1 .712.787l-.275 5.5a.75.75 0 0 1-1.498-.075l.275-5.5a.75.75 0 0 1 .786-.711Z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<div class=" self-center text-sm font-medium text-red-600 dark:text-red-400">
						{clearingCache ? $i18n.t('초기화 중...') : $i18n.t('Gemini Cache 초기화')}
					</div>
				</button>
			{/if}
		</div>
	</div>
</form>
