<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { getUsers } from '$lib/apis/users';
	import { addUserToGroup } from '$lib/apis/groups';
	import { WEBUI_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');

	export let groupId: string | undefined = undefined;
	export let userCount = 0;
	export let loading = false;

	let inputFiles: FileList | null = null;
	let fileInput: HTMLInputElement | undefined;

	const clearFileInput = () => {
		inputFiles = null;
		if (fileInput) {
			fileInput.value = '';
		}
	};

	const importCsv = async (file: File) => {
		if (!groupId) {
			clearFileInput();
			return;
		}

		loading = true;

		try {
			const csv = await file.text();
			const validRows: { idx: number; email: string }[] = [];

			for (const [idx, row] of csv.split(/\r?\n/).entries()) {
				if (idx === 0) continue;

				const columns = row.split(',').map((col) => col.trim());
				if (columns.length === 1 && columns[0] === '') continue;

				if (columns.length !== 2 || !columns[1]) {
					toast.error(`Row ${idx + 1}: invalid format.`);
					continue;
				}

				validRows.push({ idx, email: columns[1].toLowerCase() });
			}

			const userIds: string[] = [];
			const BATCH_SIZE = 10;

			for (let i = 0; i < validRows.length; i += BATCH_SIZE) {
				const batch = validRows.slice(i, i + BATCH_SIZE);
				const results = await Promise.allSettled(
					batch.map(({ idx, email }) =>
						getUsers(localStorage.token, email)
							.then((res) => {
								const user = res?.users?.find((u) => u.email?.toLowerCase() === email);
								if (user?.id) {
									return user.id;
								}

								toast.error(`Row ${idx + 1}: ${$i18n.t('User not found.')}`);
								return null;
							})
							.catch((error) => {
								toast.error(`Row ${idx + 1}: ${error}`);
								return null;
							})
					)
				);

				for (const result of results) {
					if (result.status === 'fulfilled' && result.value) {
						userIds.push(result.value);
					}
				}
			}

			if (userIds.length > 0) {
				await addUserToGroup(localStorage.token, groupId, userIds);
				userCount += userIds.length;
				toast.success(
					$i18n.t('Successfully imported {{userCount}} users.', { userCount: userIds.length })
				);
			}
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			clearFileInput();
			loading = false;
		}
	};

	const handleFileChange = async () => {
		const file = inputFiles?.[0];
		if (!file || loading) {
			return;
		}

		await importCsv(file);
	};
</script>

<div>
	<div class="mb-3 w-full">
		<input
			bind:this={fileInput}
			hidden
			bind:files={inputFiles}
			type="file"
			accept=".csv"
			disabled={loading}
			on:change={handleFileChange}
		/>

		<button
			class="w-full text-sm font-normal py-3 bg-transparent hover:bg-gray-100 border border-dashed dark:border-gray-850 dark:hover:bg-gray-850 text-center rounded-xl {loading
				? 'cursor-not-allowed opacity-60'
				: ''}"
			type="button"
			disabled={loading}
			on:click={() => {
				fileInput?.click();
			}}
		>
			{#if loading}
				{$i18n.t('Importing...')}
			{:else}
				{$i18n.t('Click here to select a csv file.')}
			{/if}
		</button>
	</div>

	<div class=" text-xs text-gray-500">
		ⓘ {$i18n.t('Ensure your CSV file includes 2 columns in this order: Name, Email.')}
		<a class="underline dark:text-gray-200" href="{WEBUI_BASE_URL}/static/group-import.csv">
			{$i18n.t('Click here to download group import template file.')}
		</a>
	</div>
</div>
