<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	import ScheduleDropdown from '$lib/components/automations/ScheduleDropdown.svelte';
	import ModelDropdown from '$lib/components/automations/ModelDropdown.svelte';

	import {
		createAutomation,
		updateAutomationById,
		type AutomationForm,
		type AutomationResponse
	} from '$lib/apis/automations';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let automation: AutomationResponse | null = null;

	let name = '';
	let prompt = '';
	let model_id = '';
	let is_active = true;

	let loading = false;

	// Schedule dropdown ref
	let scheduleDropdown: ScheduleDropdown;

	const submitHandler = async () => {
		if (!name.trim() || !prompt.trim() || !model_id.trim()) {
			toast.error($i18n.t('Name, prompt, and model are required'));
			return;
		}
		if (scheduleDropdown?.frequency === 'ONCE') {
			const scheduled = new Date(`${scheduleDropdown.onceDate}T${scheduleDropdown.onceTime}`);
			if (scheduled <= new Date()) {
				toast.error($i18n.t('Scheduled time must be in the future'));
				return;
			}
		}
		loading = true;
		try {
			const form: AutomationForm = {
				name: name.trim(),
				data: {
					prompt: prompt.trim(),
					model_id: model_id.trim(),
					rrule: scheduleDropdown.buildRrule()
				},
				is_active
			};

			if (automation) {
				await updateAutomationById(localStorage.token, automation.id, form);
				toast.success($i18n.t('Automation updated'));
				show = false;
				dispatch('save', { id: automation.id });
			} else {
				const created = await createAutomation(localStorage.token, form);
				toast.success($i18n.t('Automation created'));
				show = false;
				dispatch('save', { id: created?.id });
			}
		} catch (e: any) {
			toast.error(e?.detail ?? `${e}` ?? 'Failed to save');
		} finally {
			loading = false;
		}
	};

	const init = async () => {
		if (automation) {
			name = automation.name;
			prompt = automation.data.prompt;
			model_id = automation.data.model_id;
			is_active = automation.is_active;
			if (scheduleDropdown) {
				scheduleDropdown.parseRrule(automation.data.rrule);
			}
		} else {
			name = '';
			prompt = '';
			model_id = '';
			is_active = true;
		}
	};

	$: if (show) {
		init();
	}
</script>

<Modal size="md" bind:show>
	<div>
		<!-- Header -->
		<div class="flex justify-between dark:text-gray-100 px-5 pt-4 pb-2">
			<input
				class="w-full text-lg font-medium bg-transparent outline-hidden font-primary placeholder:text-gray-300 dark:placeholder:text-gray-700"
				type="text"
				bind:value={name}
				placeholder={$i18n.t('Automation title')}
			/>
			<button
				class="self-center shrink-0 ml-2"
				aria-label={$i18n.t('Close')}
				on:click={() => (show = false)}
			>
				<XMark className="size-5" />
			</button>
		</div>

		<!-- Prompt -->
		<div class="px-5 pb-2">
			<div class="mb-1 text-xs text-gray-500">{$i18n.t('Instructions')}</div>
			<textarea
				class="w-full text-sm bg-transparent outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700 resize-none min-h-[12rem]"
				bind:value={prompt}
				rows={8}
				placeholder={$i18n.t('Enter prompt here.')}
			/>
		</div>

		<!-- Bottom toolbar -->
		<div class="flex items-center justify-between px-4 pb-3.5 pt-1 gap-2">
			<div class="flex items-center gap-0.5 flex-wrap flex-1 min-w-0">
				<ScheduleDropdown bind:this={scheduleDropdown} side="top" align="start" />

				<ModelDropdown bind:model_id side="top" align="start" />
			</div>

			<div class="flex items-center gap-2 shrink-0">
				<button
					class="px-3 py-1 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-200 transition"
					type="button"
					on:click={() => (show = false)}
				>
					{$i18n.t('Cancel')}
				</button>
				<button
					class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex items-center gap-2 {loading
						? 'cursor-not-allowed'
						: ''}"
					on:click={submitHandler}
					type="button"
					disabled={loading}
				>
					{automation ? $i18n.t('Save') : $i18n.t('Create')}
					{#if loading}
						<span class="shrink-0"><Spinner /></span>
					{/if}
				</button>
			</div>
		</div>
	</div>
</Modal>
