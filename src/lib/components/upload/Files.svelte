<script lang="ts">
	import { browser } from '$app/environment';
	import { deleteUpload, getFiles, rebuildUserArtifact, type StoredFile } from '$lib/apis/uploads';
	import { user } from '$lib/stores';
	import { toast } from 'svelte-sonner';

	export let tenantId: string | null = null;
	export let path: string | null = null;
	export let tenantBucket: string | null = null;

	let files: StoredFile[] = [];
	let loading = false;
	let error: string | null = null;
	let lastParams = '';
	let deletingKey: string | null = null;

	const formatSize = (bytes: number) => {
		if (!bytes) return '0 B';
		const units = ['B', 'KB', 'MB', 'GB', 'TB'];
		const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
		const value = bytes / Math.pow(1024, exponent);
		return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[exponent]}`;
	};
	const normalizePath = (value: string) => (value.endsWith('/') ? value : `${value}/`);

	const displayName = (key: string) => {
		if (!path) return key;
		const prefix = normalizePath(path);
		return key.startsWith(prefix) ? key.slice(prefix.length) : key;
	};

	const loadFiles = async () => {
		if (!browser || !path || !localStorage.token) {
			files = [];
			error = path ? null : 'No path selected.';
			return;
		}

		loading = true;
		error = null;
		try {
			files = await getFiles(localStorage.token, path, tenantId ?? undefined);
		} catch (err) {
			const message = typeof err === 'string' ? err : err?.detail ?? 'Failed to load files.';
			error = message;
			toast.error(message);
			files = [];
		} finally {
			loading = false;
		}
	};

	$: paramsKey = path ? `${tenantId ?? 'self'}|${path}` : '';
	$: if (browser && paramsKey && paramsKey !== lastParams) {
		lastParams = paramsKey;
		loadFiles();
	}

	const deleteFileHandler = async (file: StoredFile) => {
		if (!browser) return;
		if (!localStorage.token) {
			toast.error('You must be signed in to delete files.');
			return;
		}

		const name = displayName(file.key);
		const confirmed = window.confirm(`Delete ${name}? This cannot be undone.`);
		if (!confirmed) return;

		const parts = file.key.split('/');
		const derivedBucket = tenantBucket ?? (parts[0] ?? null);
		const derivedUserId = parts.length >= 3 && parts[1] === 'users' ? parts[2] : null;

		deletingKey = file.key;
		try {
			const token = localStorage.token;
			await deleteUpload(token, file.key);
			files = files.filter((item) => item.key !== file.key);
			toast.success('File deleted.');

			if (derivedBucket && derivedUserId) {
				try {
					await rebuildUserArtifact(token, derivedBucket, derivedUserId);
					toast.success('Private artifact rebuild requested.');
				} catch (err) {
					const message =
						typeof err === 'string'
							? err
							: (err?.detail ?? 'Failed to rebuild private artifact.');
					toast.error(message);
				}
			}
		} catch (err) {
			const message = typeof err === 'string' ? err : err?.detail ?? 'Failed to delete file.';
			toast.error(message);
		} finally {
			deletingKey = null;
		}
	};
</script>

{#if loading}
	<div class="rounded-2xl border border-gray-100 bg-white/60 p-5 text-sm shadow-sm dark:border-gray-850 dark:bg-gray-900/70">
		Loading files…
	</div>
{:else if error}
	<div class="rounded-2xl border border-red-200 bg-red-50/70 p-5 text-sm text-red-900 shadow-sm dark:border-red-500/40 dark:bg-red-500/10 dark:text-red-100">
		{error}
	</div>
{:else if files.length === 0}
	<div class="rounded-2xl border border-gray-100 bg-white/70 p-5 text-sm text-gray-600 shadow-sm dark:border-gray-850 dark:bg-gray-900/70 dark:text-gray-300">
		No files found for this path.
	</div>
{:else}
	<div class="overflow-x-auto rounded-2xl border border-gray-100 bg-white/70 shadow-sm dark:border-gray-850 dark:bg-gray-900/70">
		<table class="min-w-full divide-y divide-gray-200 dark:divide-gray-800 text-sm">
			<thead class="bg-gray-50 dark:bg-gray-900/80 text-gray-600 dark:text-gray-300">
				<tr>
					<th class="px-4 py-3 text-left font-semibold">File</th>
					<th class="px-4 py-3 text-left font-semibold">Size</th>
					<th class="px-4 py-3 text-left font-semibold">Last Modified</th>
					<th class="px-4 py-3 text-left font-semibold">Actions</th>
				</tr>
			</thead>
			<tbody class="divide-y divide-gray-100 dark:divide-gray-850 text-gray-800 dark:text-gray-100">
				{#each files as file}
					<tr>
						<td class="px-4 py-3 font-mono text-xs sm:text-sm break-all">
							{displayName(file.key)}
						</td>
						<td class="px-4 py-3">{formatSize(file.size)}</td>
						<td class="px-4 py-3">
							{new Date(file.last_modified).toLocaleString()}
						</td>
						<td class="px-4 py-3">
							<div class="inline-flex flex-col gap-2">
								<!-- TODO Downloading does not work locally.... might fix itself live?-->
								<a
									href={file.url}
									target="_blank"
									rel="noreferrer"
									class="inline-flex w-28 items-center justify-center rounded-lg border border-blue-600 px-3 py-1.5 text-xs font-medium text-blue-600 transition hover:bg-blue-50 dark:hover:bg-blue-950/30"
								>
									Download
								</a>
								<button
									type="button"
									on:click={() => deleteFileHandler(file)}
									disabled={deletingKey === file.key}
									class="inline-flex w-28 items-center justify-center rounded-lg border border-red-600 px-3 py-1.5 text-xs font-medium text-red-600 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-70 dark:hover:bg-red-950/30"
								>
									{deletingKey === file.key ? 'Deleting...' : 'Delete'}
								</button>
							</div>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
{/if}
