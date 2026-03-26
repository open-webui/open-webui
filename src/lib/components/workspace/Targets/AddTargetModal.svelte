<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import type { NewTargetInput, TargetType } from './types';

	const i18n = getContext<any>('i18n');
	const dispatch = createEventDispatcher<{ submit: NewTargetInput }>();

	export let show = false;

	const defaultForm: NewTargetInput = {
		name: '',
		type: 'Domain',
		value: '',
		description: ''
	};

	let form: NewTargetInput = { ...defaultForm };

	$: if (show) {
		form = { ...defaultForm };
	}

	const targetTypes: TargetType[] = ['Domain', 'IP', 'URL', 'CIDR', 'Host'];

	const submitHandler = () => {
		dispatch('submit', {
			name: form.name.trim(),
			type: form.type,
			value: form.value.trim(),
			description: form.description.trim()
		});
		show = false;
	};
</script>

<Modal size="sm" bind:show>
	<div>
		<div
			class="flex justify-between dark:text-gray-200 px-5 pt-4 pb-2 border-b border-sky-100/80 dark:border-sky-900/45"
		>
			<div class="text-lg font-medium self-center">{$i18n.t('Add Target')}</div>
			<button
				class="self-center rounded-lg p-1 hover:bg-sky-100/80 dark:hover:bg-sky-900/45 transition"
				aria-label={$i18n.t('Close')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark className="size-5" />
			</button>
		</div>

		<form class="px-5 pb-4 text-sm" on:submit|preventDefault={submitHandler}>
			<div class="flex flex-col gap-3">
				<div>
					<div class="mb-1 text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Name')}</div>
					<input
						class="w-full text-sm bg-white/75 dark:bg-slate-900/60 border border-sky-100/80 dark:border-sky-900/45 rounded-lg px-2.5 py-2 outline-hidden"
						type="text"
						bind:value={form.name}
						placeholder={$i18n.t('Production API Surface')}
						required
					/>
				</div>

				<div>
					<div class="mb-1 text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Type')}</div>
					<select
						class="w-full rounded-lg text-sm bg-white/75 dark:bg-slate-900/60 border border-sky-100/80 dark:border-sky-900/45 px-2.5 py-2 outline-hidden"
						bind:value={form.type}
					>
						{#each targetTypes as type}
							<option value={type}>{type}</option>
						{/each}
					</select>
				</div>

				<div>
					<div class="mb-1 text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Value')}</div>
					<input
						class="w-full text-sm bg-white/75 dark:bg-slate-900/60 border border-sky-100/80 dark:border-sky-900/45 rounded-lg px-2.5 py-2 outline-hidden"
						type="text"
						bind:value={form.value}
						placeholder={$i18n.t('api.example.com')}
						required
					/>
				</div>

				<div>
					<div class="mb-1 text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Description')}</div>
					<textarea
						class="w-full text-sm bg-white/75 dark:bg-slate-900/60 border border-sky-100/80 dark:border-sky-900/45 rounded-lg px-2.5 py-2 outline-hidden resize-none"
						bind:value={form.description}
						rows="3"
						placeholder={$i18n.t('Optional context for this target asset')}
					></textarea>
				</div>
			</div>

			<div class="mt-4 flex justify-end gap-2">
				<button
					type="button"
					class="px-3 py-1.5 rounded-xl bg-slate-100/85 hover:bg-slate-200/85 dark:bg-slate-800/70 dark:hover:bg-slate-700/80 transition"
					on:click={() => {
						show = false;
					}}
				>
					{$i18n.t('Cancel')}
				</button>
				<button
					type="submit"
					class="px-3 py-1.5 rounded-xl bg-sky-600 text-white hover:bg-sky-500 dark:bg-sky-500 dark:hover:bg-sky-400 transition font-medium"
				>
					{$i18n.t('Add Target')}
				</button>
			</div>
		</form>
	</div>
</Modal>
