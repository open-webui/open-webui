<script>
	import { toast } from 'svelte-sonner';

	import { goto } from '$app/navigation';
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { user } from '$lib/stores';
	import { createNewKnowledge, updateKnowledgeById } from '$lib/apis/knowledge';

	import AccessControl from '../common/AccessControl.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';

	export let modal = false;
	export let edit = false;
	/** @type {{ id: string; name: string; description: string; access_grants?: any[]; meta?: any } | null} */
	export let knowledge = null;
	/** @type {() => void | Promise<void>} */
	export let onBack = () => goto('/workspace/knowledge');
	/** @type {(knowledge: { id: string; name: string; description: string; meta?: any; access_grants?: any[] }) => void | Promise<void>} */
	export let onSaved = (knowledge) => goto(`/workspace/knowledge/${knowledge.id}`);

	let loading = false;

	let name = knowledge?.name ?? '';
	let description = knowledge?.description ?? '';
	/** @type {{ id?: string; principal_type: 'user' | 'group'; principal_id: string; permission: 'read' | 'write' }[]} */
	let accessGrants = [];
	let showAdvanced = false;
	/** @type {number | undefined} */
	let maxFileCount = knowledge?.meta?.max_file_count || undefined;
	/** @type {number | undefined} */
	let maxFileSize = knowledge?.meta?.max_file_size || undefined;

	const submitHandler = async () => {
		if (loading) return;
		if (name.trim() === '' || description.trim() === '') {
			toast.error($i18n.t('Please fill in all fields.'));
			return;
		}

		loading = true;
		const meta = {
			max_file_count: maxFileCount ?? null,
			max_file_size: maxFileSize ?? null
		};
		try {
			const res =
				edit && knowledge
					? await updateKnowledgeById(localStorage.token, knowledge.id, {
							name,
							description,
							meta
						})
					: await createNewKnowledge(localStorage.token, name, description, accessGrants, meta);
			if (res) {
				toast.success($i18n.t(edit ? 'Saved' : 'Knowledge created successfully.'));
				await onSaved(res);
			}
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			loading = false;
		}
	};
</script>

<div class="w-full max-h-full">
	{#if modal}
		<div class="flex justify-between items-center dark:text-gray-100 px-5 pt-4 pb-2">
			<h3 class="text-base font-normal">
				{$i18n.t(edit ? 'Settings' : 'Create a knowledge base')}
			</h3>
			<button
				class="self-center shrink-0 ml-2"
				aria-label={$i18n.t('Close')}
				type="button"
				on:click={() => {
					onBack();
				}}
			>
				<XMark className="size-5" />
			</button>
		</div>
	{:else}
		<button
			class="flex space-x-1"
			on:click={() => {
				onBack();
			}}
		>
			<div class=" self-center">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-4 h-4"
				>
					<path
						fill-rule="evenodd"
						d="M17 10a.75.75 0 01-.75.75H5.612l4.158 3.96a.75.75 0 11-1.04 1.08l-5.5-5.25a.75.75 0 010-1.08l5.5-5.25a.75.75 0 111.04 1.08L5.612 9.25H16.25A.75.75 0 0117 10z"
						clip-rule="evenodd"
					/>
				</svg>
			</div>
			<div class=" self-center font-normal text-sm">{$i18n.t('Back')}</div>
		</button>
	{/if}

	<form
		class="flex flex-col {modal ? 'px-5 pb-3' : 'max-w-lg mx-auto mt-10 mb-10'}"
		on:submit|preventDefault={() => {
			submitHandler();
		}}
	>
		<div class="w-full flex flex-col {modal ? '' : 'justify-center'}">
			{#if !modal}
				<div class=" text-2xl font-normal mb-2.5">
					{$i18n.t(edit ? 'Settings' : 'Create a knowledge base')}
				</div>
			{/if}

			<div class="w-full flex flex-col gap-2.5">
				<div class="w-full">
					<div class="{modal ? 'text-xs text-gray-500' : 'text-sm'} mb-2">
						{$i18n.t('What are you working on?')}
					</div>

					<div class="w-full mt-1">
						<input
							class={modal
								? 'w-full text-sm bg-transparent outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'
								: 'w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden'}
							type="text"
							bind:value={name}
							placeholder={$i18n.t('Name your knowledge base')}
							required
						/>
					</div>
				</div>

				<div>
					<div class="{modal ? 'text-xs text-gray-500' : 'text-sm'} mb-2">
						{$i18n.t('What are you trying to achieve?')}
					</div>

					<div class="w-full mt-1">
						<textarea
							class={modal
								? 'w-full resize-none text-sm bg-transparent outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'
								: 'w-full resize-none rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden'}
							rows={modal ? 6 : 4}
							bind:value={description}
							placeholder={$i18n.t('Describe your knowledge base and objectives')}
							required
						></textarea>
					</div>
				</div>
			</div>
		</div>

		{#if !edit}
			<div class="mt-2">
				<AccessControl
					bind:accessGrants
					accessRoles={['read', 'write']}
					share={$user?.permissions?.sharing?.knowledge || $user?.role === 'admin'}
					sharePublic={$user?.permissions?.sharing?.public_knowledge || $user?.role === 'admin'}
					shareUsers={($user?.permissions?.access_grants?.allow_users ?? true) ||
						$user?.role === 'admin'}
					allowGroups={($user?.permissions?.access_grants?.allow_groups ?? true) ||
						$user?.role === 'admin'}
				/>
			</div>
		{/if}

		<button
			type="button"
			class="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition mt-3 self-start"
			aria-expanded={showAdvanced}
			aria-controls="knowledge-advanced"
			on:click={() => (showAdvanced = !showAdvanced)}
		>
			<ChevronRight className={`size-3 transition-transform ${showAdvanced ? 'rotate-90' : ''}`} />
			{$i18n.t('Advanced')}
		</button>

		{#if showAdvanced}
			<div id="knowledge-advanced" class="mt-3 space-y-3">
				<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
					<div>
						<label for="knowledge-max-file-count" class="block text-xs text-gray-500 mb-2">
							{$i18n.t('File count limit')}
						</label>
						<input
							id="knowledge-max-file-count"
							type="number"
							min="1"
							step="1"
							class="w-full text-sm bg-transparent outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700"
							placeholder={$i18n.t('Use global setting')}
							bind:value={maxFileCount}
						/>
						<p class="mt-1 text-xs text-gray-500">{$i18n.t('Maximum total files.')}</p>
					</div>
					<div>
						<label for="knowledge-max-file-size" class="block text-xs text-gray-500 mb-2"
							>{$i18n.t('File size limit (MB)')}</label
						>
						<input
							id="knowledge-max-file-size"
							type="number"
							min="1"
							step="1"
							class="w-full text-sm bg-transparent outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700"
							placeholder={$i18n.t('Use global setting')}
							bind:value={maxFileSize}
						/>
						<p class="mt-1 text-xs text-gray-500">{$i18n.t('Maximum size per file.')}</p>
					</div>
				</div>
				<p class="text-xs text-gray-500">
					{$i18n.t('Global limits always apply.')}
				</p>
			</div>
		{/if}

		<div class="flex justify-end {modal ? 'pt-3 gap-2' : 'mt-2'}">
			{#if modal}
				<button
					class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg px-2.5 text-xs font-normal text-gray-600 transition hover:bg-gray-100 hover:text-gray-900 disabled:opacity-60 dark:text-gray-400 dark:hover:bg-gray-850 dark:hover:text-white"
					type="button"
					on:click={() => {
						onBack();
					}}
				>
					{$i18n.t('Cancel')}
				</button>
			{/if}

			<div>
				<button
					class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg px-2.5 text-xs font-normal transition disabled:opacity-60 disabled:cursor-not-allowed {modal
						? 'bg-gray-900 text-white hover:bg-black dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white'
						: 'bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800'}"
					type="submit"
					disabled={loading}
				>
					<div class=" self-center font-normal">{$i18n.t(edit ? 'Save' : 'Create Knowledge')}</div>

					{#if loading}
						<div class="shrink-0">
							<Spinner className="size-3" />
						</div>
					{/if}
				</button>
			</div>
		</div>
	</form>
</div>
