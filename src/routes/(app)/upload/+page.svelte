<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { uploadDocument, type UploadDocumentResponse, type UploadVisibility } from '$lib/apis/uploads';
	import { WEBUI_NAME, user } from '$lib/stores';

	let visibility: UploadVisibility = 'public';
	let selectedFile: File | null = null;
	let isUploading = false;
	let uploadResult: UploadDocumentResponse | null = null;
	let fileInput: HTMLInputElement | null = null;

	const handleFileChange = (event: Event) => {
		const target = event.target as HTMLInputElement;
		selectedFile = target.files?.[0] ?? null;
	};

	const formatBytes = (bytes: number) => {
		if (!bytes) return '0 B';
		const units = ['B', 'KB', 'MB', 'GB', 'TB'];
		const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
		const value = bytes / Math.pow(1024, exponent);
		return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[exponent]}`;
	};

	const handleSubmit = async (event: SubmitEvent) => {
		event.preventDefault();
		if (!selectedFile) {
			toast.error('Please choose a file to upload.');
			return;
		}

		if (!$user?.tenant_s3_bucket) {
			toast.error('Your tenant does not have an S3 bucket configured.');
			return;
		}

		if (!localStorage.token) {
			toast.error('You must be signed in to upload files.');
			return;
		}

		isUploading = true;
		uploadResult = null;

		try {
			const result = await uploadDocument(localStorage.token, selectedFile, visibility);
			uploadResult = result;
			toast.success('Upload complete.');
			selectedFile = null;
			if (fileInput) {
				fileInput.value = '';
			}
		} catch (err) {
			const message = typeof err === 'string' ? err : err?.detail ?? 'Failed to upload file.';
			toast.error(message);
		} finally {
			isUploading = false;
		}
	};

	$: tenantBucket = $user?.tenant_s3_bucket ?? null;
	$: destinationPreview = tenantBucket
		? `${tenantBucket}${visibility === 'private' ? `/users/${$user?.id}` : ''}/${
				selectedFile?.name ?? 'your-file.ext'
			}`
		: null;
</script>

<svelte:head>
	<title>Uploads • {$WEBUI_NAME}</title>
</svelte:head>

<div class="px-4 py-6 sm:px-6 lg:px-8">
	<div class="mx-auto flex max-w-3xl flex-col gap-6">
		<div class="space-y-2">
			<h1 class="text-3xl font-semibold text-gray-900 dark:text-gray-50">Uploads</h1>
			<p class="text-sm text-gray-600 dark:text-gray-400">
				Upload documents directly to tenant-scoped folders in S3. Choose whether the file should be
				shared with everyone in your tenant or live inside your private user folder.
			</p>
		</div>

		{#if !$user}
			<div class="rounded-2xl border border-gray-100 bg-white/60 p-5 text-sm shadow-sm dark:border-gray-800 dark:bg-gray-900">
				Loading your profile…
			</div>
		{:else if !tenantBucket}
			<div class="rounded-2xl border border-amber-200 bg-amber-50/80 p-5 text-sm text-amber-900 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-100">
				Your tenant does not have an S3 bucket configured yet. Please contact an administrator before
				using this page.
			</div>
		{:else}
			<div class="rounded-2xl border border-gray-100 bg-white/70 p-5 shadow-sm dark:border-gray-850 dark:bg-gray-900/80">
				<div class="space-y-3 text-sm text-gray-700 dark:text-gray-300">
						<p>
							Files are stored inside
							<code class="rounded bg-gray-100 px-1.5 py-0.5 text-xs dark:bg-gray-850">
								{tenantBucket}
							</code>
							in the configured S3 bucket with two destinations:
						</p>
					<ul class="list-disc space-y-1 pl-6">
						<li>
							<span class="font-medium text-gray-900 dark:text-gray-100">Public</span>
								<span class="text-gray-600 dark:text-gray-400">
									→
									<code class="rounded bg-gray-100 px-1 py-0.5 text-xs dark:bg-gray-850">
										{tenantBucket}/&lt;filename&gt;
									</code>
								</span>
						</li>
						<li>
							<span class="font-medium text-gray-900 dark:text-gray-100">Private</span>
								<span class="text-gray-600 dark:text-gray-400">
									→
									<code class="rounded bg-gray-100 px-1 py-0.5 text-xs dark:bg-gray-850">
										{tenantBucket}/users/{$user?.id}/&lt;filename&gt;
									</code>
								</span>
						</li>
					</ul>
				</div>
			</div>

			<form class="space-y-5 rounded-2xl border border-gray-100 bg-white/80 p-5 shadow-sm dark:border-gray-850 dark:bg-gray-900/80" on:submit|preventDefault={handleSubmit}>
				<div class="space-y-2">
					<label class="text-sm font-medium text-gray-900 dark:text-gray-100">Visibility</label>
					<select
						class="w-full rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none dark:border-gray-800 dark:bg-gray-900 dark:text-gray-50"
						bind:value={visibility}
					>
						<option value="public">Public (shared tenant folder)</option>
						<option value="private">Private (your user folder)</option>
					</select>
				</div>

				<div class="space-y-2">
					<label class="text-sm font-medium text-gray-900 dark:text-gray-100">File</label>
					<input
						class="block w-full rounded-xl border border-dashed border-gray-300 bg-gray-50 px-4 py-3 text-sm text-gray-800 file:mr-4 file:rounded-lg file:border-0 file:bg-blue-600 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:border-gray-400 focus:border-blue-500 focus:outline-none dark:border-gray-800 dark:bg-gray-900 dark:text-gray-100"
						type="file"
						required
						on:change={handleFileChange}
						bind:this={fileInput}
					/>
					{#if selectedFile}
						<p class="text-xs text-gray-500 dark:text-gray-400">
							<span class="font-medium text-gray-700 dark:text-gray-200">{selectedFile.name}</span>
							• {formatBytes(selectedFile.size)}
						</p>
					{/if}
				</div>

				{#if destinationPreview}
					<div class="rounded-xl bg-gray-50 px-3 py-2 text-xs text-gray-600 dark:bg-gray-900 dark:text-gray-300">
						<div class="text-[11px] uppercase tracking-wide text-gray-400">Destination Preview</div>
						<code class="break-all">{destinationPreview}</code>
					</div>
				{/if}

				<div class="flex flex-wrap gap-3">
					<button
						type="submit"
						class="inline-flex items-center justify-center rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-blue-400"
						disabled={!selectedFile || isUploading}
					>
						{#if isUploading}
							<span class="animate-pulse">Uploading…</span>
						{:else}
							Upload file
						{/if}
					</button>
					<button
						type="button"
						class="inline-flex items-center justify-center rounded-xl border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 transition hover:border-gray-300 hover:text-gray-900 dark:border-gray-800 dark:text-gray-200 dark:hover:border-gray-700 dark:hover:text-white"
						on:click={() => {
							selectedFile = null;
							uploadResult = null;
							if (fileInput) {
								fileInput.value = '';
							}
						}}
					>
						Reset
					</button>
				</div>
			</form>
		{/if}

		{#if uploadResult}
			<div class="rounded-2xl border border-emerald-200 bg-emerald-50/80 p-5 text-sm text-emerald-900 shadow-sm dark:border-emerald-500/40 dark:bg-emerald-500/10 dark:text-emerald-100">
				<h2 class="text-lg font-semibold text-emerald-900 dark:text-emerald-100">Upload complete</h2>
				<dl class="mt-3 space-y-2">
					<div>
						<dt class="text-xs uppercase tracking-wide text-emerald-700/80 dark:text-emerald-200/80">
							S3 URL
						</dt>
						<dd class="font-mono text-sm text-emerald-900 dark:text-emerald-50 break-all">{uploadResult.url}</dd>
					</div>
					<div>
						<dt class="text-xs uppercase tracking-wide text-emerald-700/80 dark:text-emerald-200/80">
							Object Key
						</dt>
						<dd class="font-mono text-sm text-emerald-900 dark:text-emerald-50 break-all">
							{uploadResult.key}
						</dd>
					</div>
					<div class="flex flex-wrap gap-4">
						<div>
							<dt class="text-xs uppercase tracking-wide text-emerald-700/80 dark:text-emerald-200/80">
								Visibility
							</dt>
							<dd class="font-semibold capitalize">{uploadResult.visibility}</dd>
						</div>
						<div>
							<dt class="text-xs uppercase tracking-wide text-emerald-700/80 dark:text-emerald-200/80">
								Stored Name
							</dt>
							<dd class="font-mono text-sm text-emerald-900 dark:text-emerald-50">
								{uploadResult.stored_filename}
							</dd>
						</div>
					</div>
				</dl>
			</div>
		{/if}
	</div>
</div>
