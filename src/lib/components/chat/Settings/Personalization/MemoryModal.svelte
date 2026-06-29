<script>
	import { createEventDispatcher, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { addNewMemory, updateMemoryById } from '$lib/apis/memories';

	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const dispatch = createEventDispatcher();

	export let show;
	export let memory = null;

	const i18n = getContext('i18n');

	let loading = false;
	let content = '';
	let type = 'user';
	let path = '';

	$: edit = !!memory?.id;
	$: if (show) {
		content = memory?.content ?? '';
		type = memory?.type ?? 'user';
		path = memory?.path ?? '';
	}

	const submitHandler = async () => {
		loading = true;

		const res = await (
			edit
				? updateMemoryById(localStorage.token, memory.id, content, type, path)
				: addNewMemory(localStorage.token, content, type, path)
		).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success(
				edit ? $i18n.t('Memory updated successfully') : $i18n.t('Memory added successfully')
			);
			show = false;
			dispatch('save');
		}

		loading = false;
	};
</script>

<Modal bind:show size="sm">
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-2">
			<div class=" text-lg font-medium self-center">
				{#if edit}
					{$i18n.t('Edit Memory')}
				{:else}
					{$i18n.t('Add Memory')}
				{/if}
			</div>
			<button class="self-center" on:click={() => (show = false)}>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-5 pb-4 md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form class="flex flex-col w-full" on:submit|preventDefault={submitHandler}>
					<div class="px-1">
						<div class="flex w-full justify-between items-center mb-1.5">
							<div class="text-xs text-gray-500">{$i18n.t('Type')}</div>

							<button
								type="button"
								class="text-xs text-gray-700 dark:text-gray-300"
								on:click={() => {
									type = type === 'user' ? 'context' : 'user';
								}}
							>
								{#if type === 'user'}
									{$i18n.t('User')}
								{:else}
									{$i18n.t('Context')}
								{/if}
							</button>
						</div>

						<textarea
							bind:value={content}
							class="bg-transparent w-full text-sm outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700"
							rows="6"
							style="resize: vertical;"
							placeholder={type === 'user'
								? $i18n.t('Add a preference, fact, or instruction about you')
								: $i18n.t('Add durable context for future chats')}
						/>

						<div class="flex flex-col w-full mt-1.5">
							<label for="memory-path" class="mb-0.5 text-xs text-gray-500">
								{$i18n.t('Path')}
								<span class="opacity-50">({$i18n.t('optional')})</span>
							</label>

							<input
								id="memory-path"
								bind:value={path}
								class="w-full text-sm bg-transparent outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700"
								placeholder={$i18n.t('Path')}
								autocomplete="off"
							/>
						</div>
					</div>

					<div class="flex justify-end pt-1 text-sm font-medium">
						<button
							class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex items-center gap-2 whitespace-nowrap {loading
								? ' cursor-not-allowed'
								: ''}"
							type="submit"
							disabled={loading}
						>
							{#if edit}
								{$i18n.t('Update')}
							{:else}
								{$i18n.t('Add')}
							{/if}

							{#if loading}
								<span class="shrink-0">
									<Spinner />
								</span>
							{/if}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>
