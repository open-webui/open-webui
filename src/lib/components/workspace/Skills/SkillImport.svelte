<script lang="ts">
	import Modal from '$lib/components/common/Modal.svelte';
	import { toast } from 'svelte-sonner';
	import { importSkillBundles, skillError } from '$lib/apis/skills';
	export let show = false;
	export let files: File[] = [];
	export let onImported: () => Promise<void> = async () => {};
	let loading = false;
	let items: any[] = [];
	let results: any[] = [];
	let loadedFiles: File[] | null = null;
	$: if (show && files !== loadedFiles) {
		loadedFiles = files;
		preview();
	}
	const preview = async () => {
		loading = true;
		results = [];
		items = [];
		try {
			items = (await importSkillBundles(localStorage.token, files)).map((item: any) => ({
				...item,
				action: item.id_taken || item.name_taken ? 'skip' : 'create'
			}));
		} catch (error) {
			toast.error(skillError(error));
		} finally {
			loading = false;
		}
	};
	const save = async () => {
		loading = true;
		try {
			results = await importSkillBundles(
				localStorage.token,
				files,
				items.map(({ action, id, name, expected_version_id }) => ({
					action,
					id,
					name,
					expected_version_id
				}))
			);
			results.forEach((result, index) => {
				if (result.status === 'saved') items[index].action = 'skip';
			});
			items = [...items];
			if (results.some((r) => r.status === 'saved')) await onImported();
		} catch (error) {
			toast.error(skillError(error));
		} finally {
			loading = false;
		}
	};
</script>

<Modal bind:show size="lg">
	<div class="p-5">
		<div class="mb-3 flex justify-between">
			<h2 class="font-medium">Import skills</h2>
			<button type="button" on:click={() => (show = false)}>Close</button>
		</div>
		<p class="mb-3 text-xs text-gray-500">
			New skills and copies are private. Replace saves a new version and preserves existing sharing.
		</p>
		<div class="max-h-[60vh] space-y-3 overflow-auto">
			{#each items as item, index}
				<div class="rounded-lg border p-3 dark:border-gray-800">
					<div class="flex flex-wrap gap-2">
						<input
							aria-label="Skill name"
							class="min-w-0 flex-1 bg-transparent"
							bind:value={item.name}
							disabled={loading}
						/>
						<select
							aria-label="Import action"
							class="rounded bg-transparent text-xs"
							bind:value={item.action}
							disabled={loading}
						>
							<option value="create">Create</option><option value="copy">Create copy</option
							>{#if item.can_replace}<option value="replace">Replace</option>{/if}<option
								value="skip">Skip</option
							>
						</select>
					</div>
					<input
						aria-label="Skill ID"
						class="mt-2 w-full bg-transparent font-mono text-xs"
						bind:value={item.id}
						disabled={loading || item.action === 'replace'}
					/>
					{#if item.id_taken || item.name_taken}<p class="mt-1 text-xs text-amber-600">
							ID or name already exists. Choose a unique ID and name for a copy.
						</p>{/if}
					<details class="mt-2 text-xs">
						<summary>{item.files.length} files</summary>{#each item.files as file}<div
								class="font-mono"
							>
								{file.path} ({file.size} bytes)
							</div>{/each}
					</details>
					{#if results[index]}<p
							class="mt-2 text-xs"
							class:text-red-500={results[index].status === 'error'}
						>
							{results[index].status}{results[index].error
								? `: ${skillError(results[index].error)}`
								: ''}
						</p>{/if}
				</div>
			{/each}
		</div>
		<button
			type="button"
			class="mt-4 rounded-lg bg-black px-3 py-2 text-sm text-white disabled:opacity-50 dark:bg-white dark:text-black"
			disabled={loading || !items.length || items.every((i) => i.action === 'skip')}
			on:click={save}>{loading ? 'Loading…' : 'Import selected'}</button
		>
	</div>
</Modal>
