<script>
	import { toast } from 'svelte-sonner';

	import { goto } from '$app/navigation';
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { user } from '$lib/stores';
	import { createNewKnowledge } from '$lib/apis/knowledge';

	import AccessControl from '../common/AccessControl.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let modal = false;
	/** @type {() => void | Promise<void>} */
	export let onBack = () => goto('/workspace/knowledge');
	/** @type {(knowledge: { id: string }) => void | Promise<void>} */
	export let onCreated = (knowledge) => goto(`/workspace/knowledge/${knowledge.id}`);

	let loading = false;

	let name = '';
	let description = '';
	/** @type {{ id?: string; principal_type: 'user' | 'group'; principal_id: string; permission: 'read' | 'write' }[]} */
	let accessGrants = [];

	const submitHandler = async () => {
		loading = true;

		if (name.trim() === '' || description.trim() === '') {
			toast.error($i18n.t('Please fill in all fields.'));
			name = '';
			description = '';
			loading = false;
			return;
		}

		const res = await createNewKnowledge(localStorage.token, name, description, accessGrants).catch(
			(e) => {
				toast.error(`${e}`);
			}
		);

		if (res) {
			toast.success($i18n.t('Knowledge created successfully.'));
			await onCreated(res);
		}

		loading = false;
	};
</script>

<div class="w-full max-h-full {modal ? 'h-full flex flex-col' : ''}">
	{#if modal}
		<div class="flex justify-between items-center dark:text-gray-100 px-5 pt-4 pb-2">
			<h3 class="text-base font-normal">{$i18n.t('Create a knowledge base')}</h3>
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
		class="flex flex-col {modal ? 'px-5 pb-3 flex-1 min-h-0' : 'max-w-lg mx-auto mt-10 mb-10'}"
		on:submit|preventDefault={() => {
			submitHandler();
		}}
	>
		<div class="w-full flex flex-col {modal ? 'flex-1 min-h-0' : 'justify-center'}">
			{#if !modal}
				<div class=" text-2xl font-normal mb-2.5">
					{$i18n.t('Create a knowledge base')}
				</div>
			{/if}

			<div class="w-full flex flex-col gap-2.5 {modal ? 'flex-1 min-h-0' : ''}">
				<div class="w-full shrink-0">
					<div class=" text-sm mb-2">{$i18n.t('What are you working on?')}</div>

					<div class="w-full mt-1">
						<input
							class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
							type="text"
							bind:value={name}
							placeholder={$i18n.t('Name your knowledge base')}
							required
						/>
					</div>
				</div>

				<div class={modal ? 'flex-1 min-h-0 flex flex-col' : ''}>
					<div class="text-sm mb-2">{$i18n.t('What are you trying to achieve?')}</div>

					<div class="w-full mt-1 {modal ? 'flex-1 min-h-0 flex' : ''}">
						<textarea
							class="w-full {modal
								? 'flex-1 min-h-0'
								: ''} resize-none rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
							rows="4"
							bind:value={description}
							placeholder={$i18n.t('Describe your knowledge base and objectives')}
							required
						></textarea>
					</div>
				</div>
			</div>
		</div>

		<div class="mt-2 shrink-0">
			<AccessControl
				bind:accessGrants
				accessRoles={['read', 'write']}
				share={$user?.permissions?.sharing?.knowledge || $user?.role === 'admin'}
				sharePublic={$user?.permissions?.sharing?.public_knowledge || $user?.role === 'admin'}
				shareUsers={($user?.permissions?.access_grants?.allow_users ?? true) ||
					$user?.role === 'admin'}
			/>
		</div>

		<div class="flex justify-end {modal ? 'pt-3 gap-2 shrink-0' : 'mt-2'}">
			{#if modal}
				<button
					class="px-3 py-1 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-200 transition"
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
					class="{modal
						? `px-3.5 py-1.5 text-sm bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full ${loading ? 'cursor-not-allowed' : ''}`
						: `text-sm px-4 py-2 transition rounded-lg ${loading ? 'cursor-not-allowed bg-gray-100 dark:bg-gray-800' : 'bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800'}`} flex"
					type="submit"
					disabled={loading}
				>
					<div class=" self-center font-normal">{$i18n.t('Create Knowledge')}</div>

					{#if loading}
						<div class="ml-1.5 self-center">
							<Spinner />
						</div>
					{/if}
				</button>
			</div>
		</div>
	</form>
</div>
