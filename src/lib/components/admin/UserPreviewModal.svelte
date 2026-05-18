<script lang="ts">
	import { getContext } from 'svelte';
	import { getUserPreview } from '$lib/apis/users';
	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let userId: string = '';
	export let userName: string = '';

	let loading = true;
	let preview: any = null;
	let error: string = '';

	$: if (show && userId) {
		loadPreview();
	}

	const loadPreview = async () => {
		loading = true;
		error = '';
		try {
			preview = await getUserPreview(localStorage.token, userId);
		} catch (e) {
			error = String(e);
		} finally {
			loading = false;
		}
	};
</script>

<Modal size="md" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-100 px-5 pt-4 mb-1.5">
			<div class=" text-lg font-medium self-center font-primary">
				{$i18n.t('User Preview')}
				{#if userName}
					<span class="text-sm font-normal text-gray-500 ml-1">{userName}</span>
				{/if}
			</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div class="flex flex-col w-full px-5 pb-4">
			{#if loading}
				<div class="flex justify-center items-center py-8">
					<Spinner className="size-5" />
				</div>
			{:else if error}
				<div class="text-red-500 text-xs text-center py-4">{error}</div>
			{:else if preview}
				<div class="space-y-2">
					{#if preview.groups.length > 0}
						<div>
							<div class=" mb-2 text-sm font-medium">{$i18n.t('Groups')}</div>
							<div class="flex flex-col w-full">
								{#each preview.groups as group}
									<div class="flex w-full justify-between my-1">
										<div class=" self-center text-xs font-medium">{group.name}</div>
									</div>
								{/each}
							</div>
						</div>

						<hr class="border-gray-50 dark:border-gray-850/30 my-1" />
					{/if}

					<div>
						<div class=" mb-2 text-sm font-medium">{$i18n.t('Models')}</div>
						<div class="flex flex-col w-full">
							{#if preview.models.items.length === 0}
								<div class="flex w-full justify-between my-1">
									<div class=" self-center text-xs text-gray-500">
										{$i18n.t('No models accessible')}
									</div>
								</div>
							{:else}
								{#each preview.models.items as model}
									<div class="flex w-full justify-between my-1">
										<div class=" self-center text-xs font-medium">{model.name}</div>
									</div>
								{/each}

								{#if preview.models.total > preview.models.items.length}
									<div class="flex w-full justify-between my-1">
										<div class=" self-center text-xs text-gray-500">
											{$i18n.t('{{count}} of {{total}} accessible', {
												count: preview.models.items.length,
												total: preview.models.total
											})}
										</div>
									</div>
								{/if}
							{/if}
						</div>
					</div>

					<hr class="border-gray-50 dark:border-gray-850/30 my-1" />

					<div>
						<div class=" mb-2 text-sm font-medium">{$i18n.t('Knowledge')}</div>
						<div class="flex flex-col w-full">
							{#if preview.knowledge.items.length === 0}
								<div class="flex w-full justify-between my-1">
									<div class=" self-center text-xs text-gray-500">
										{$i18n.t('No knowledge bases accessible')}
									</div>
								</div>
							{:else}
								{#each preview.knowledge.items as kb}
									<div class="flex w-full justify-between my-1">
										<div class=" self-center text-xs font-medium">{kb.name}</div>
									</div>
								{/each}

								{#if preview.knowledge.total > preview.knowledge.items.length}
									<div class="flex w-full justify-between my-1">
										<div class=" self-center text-xs text-gray-500">
											{$i18n.t('{{count}} of {{total}} accessible', {
												count: preview.knowledge.items.length,
												total: preview.knowledge.total
											})}
										</div>
									</div>
								{/if}
							{/if}
						</div>
					</div>

					<hr class="border-gray-50 dark:border-gray-850/30 my-1" />

					<div>
						<div class=" mb-2 text-sm font-medium">{$i18n.t('Tools')}</div>
						<div class="flex flex-col w-full">
							{#if preview.tools.items.length === 0}
								<div class="flex w-full justify-between my-1">
									<div class=" self-center text-xs text-gray-500">
										{$i18n.t('No tools accessible')}
									</div>
								</div>
							{:else}
								{#each preview.tools.items as tool}
									<div class="flex w-full justify-between my-1">
										<div class=" self-center text-xs font-medium">{tool.name}</div>
									</div>
								{/each}

								{#if preview.tools.total > preview.tools.items.length}
									<div class="flex w-full justify-between my-1">
										<div class=" self-center text-xs text-gray-500">
											{$i18n.t('{{count}} of {{total}} accessible', {
												count: preview.tools.items.length,
												total: preview.tools.total
											})}
										</div>
									</div>
								{/if}
							{/if}
						</div>
					</div>
				</div>
			{/if}
		</div>
	</div>
</Modal>
