<script lang="ts">
	import { getContext, tick } from 'svelte';
	import { models, user, mobile, settings, type Model } from '$lib/stores';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import DropdownSub from '$lib/components/common/DropdownSub.svelte';
	import ModelControlSlider from './ModelControlSlider.svelte';
	import type { ModelControl } from '$lib/apis';
	import { updateUserSettings } from '$lib/apis/users';
	import { toast } from 'svelte-sonner';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Knobs from '$lib/components/icons/Knobs.svelte';
	import { localizeModelControls, resolveLocalizedModelName } from '$lib/utils/localizedContent';

	const i18n: any = getContext('i18n');
	export let selectedModels: string[] = [];
	let saving = false;
	$: modelControls = $settings?.params?.model_controls ?? {};
	let active: {
		model: Model;
		key: string;
		control: ModelControl;
		trigger: HTMLButtonElement;
	} | null = null;
	const back = async () => {
		const trigger = active?.trigger;
		active = null;
		await tick();
		if (trigger) document.getElementById(trigger.id)?.focus();
	};
	$: available = selectedModels
		.map((id) => $models.find((model) => model.id === id))
		.filter(
			(model): model is Model =>
				!!model &&
				!('direct' in model && model.direct) &&
				!('pipe' in model && model.pipe) &&
				Object.keys(model.info?.params?.model_controls ?? {}).length > 0
		);
	$: permitted =
		$user?.role === 'admin' ||
		(($user?.permissions?.chat?.controls ?? true) && ($user?.permissions?.chat?.params ?? true));
	$: rowClass = `focus-ring flex h-[1.6875rem] w-full cursor-pointer select-none items-center gap-2 rounded-xl px-2 text-left text-[0.8125rem] font-normal text-gray-700 outline-hidden transition-colors duration-75 dark:text-gray-100 ${$settings?.highContrastMode ? 'hover:bg-gray-200! dark:hover:bg-gray-800!' : 'hover:bg-gray-50/40! dark:hover:bg-gray-800/40!'}`;
	$: selectedClass = $settings?.highContrastMode
		? 'bg-gray-200 dark:bg-gray-800'
		: 'bg-gray-50/70 dark:bg-gray-800/60';
	const select = async (modelId: string, controlId: string, value: string) => {
		const previous = modelControls;
		const modelOptions = { ...modelControls[modelId] };
		if (value) modelOptions[controlId] = value;
		else delete modelOptions[controlId];
		settings.set({
			...$settings,
			params: {
				...$settings.params,
				model_controls: { ...modelControls, [modelId]: modelOptions }
			}
		});
		saving = true;
		try {
			if (!(await updateUserSettings(localStorage.token, { ui: { params: $settings.params } }))) {
				throw new Error($i18n.t('Failed to save settings'));
			}
		} catch (error) {
			settings.set({ ...$settings, params: { ...$settings.params, model_controls: previous } });
			toast.error(String(error));
		} finally {
			saving = false;
		}
	};
</script>

{#snippet summary(model: Model, key: string, control: ModelControl)}
	<span class="min-w-0 flex-1 truncate text-left">{control.label}</span>
	<span class="max-w-[55%] truncate text-gray-500 dark:text-gray-400">
		{control.options[modelControls[model.id]?.[key] ?? control.default ?? '']?.label ??
			$i18n.t('Default')}
	</span>
	<ChevronRight className="size-3.5 shrink-0 text-gray-400" />
{/snippet}

{#snippet choices(model: Model, key: string, control: ModelControl)}
	{#if control.description}
		<p class="px-2 py-1.5 text-xs leading-4 text-gray-500 dark:text-gray-400">
			{control.description}
		</p>
	{/if}
	<button
		type="button"
		role="menuitemradio"
		disabled={saving}
		aria-checked={!modelControls[model.id]?.[key]}
		class={`${rowClass} ${!modelControls[model.id]?.[key] ? selectedClass : ''}`}
		on:click={() => select(model.id, key, '')}
	>
		<span class="min-w-0 flex-1 truncate text-left">
			{$i18n.t('Default')}{#if control.options[control.default ?? '']?.label}{' · '}{control
					.options[control.default ?? ''].label}{/if}
		</span>
		{#if !modelControls[model.id]?.[key]}<Check className="size-3! shrink-0" />{/if}
	</button>
	{#each Object.entries(control.options) as [value, option] (value)}
		<button
			type="button"
			role="menuitemradio"
			disabled={saving}
			aria-checked={modelControls[model.id]?.[key] === value}
			class={`${rowClass} ${modelControls[model.id]?.[key] === value ? selectedClass : ''}`}
			on:click={() => select(model.id, key, value)}
		>
			<span class="min-w-0 flex-1 truncate text-left">{option.label}</span>
			{#if modelControls[model.id]?.[key] === value}<Check className="size-3! shrink-0" />{/if}
		</button>
	{/each}
{/snippet}

{#if permitted && available.length}
	<Dropdown align="end" visualViewportAware onOpenChange={() => (active = null)}>
		<Tooltip content={$i18n.t('Model controls')} placement="top">
			<button
				type="button"
				aria-label={$i18n.t('Model controls')}
				class="mr-2 flex shrink-0 items-center justify-center text-gray-500 transition-colors hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
			>
				<Knobs className="size-4" />
			</button>
		</Tooltip>
		<div slot="content">
			<DropdownMenu className="w-60 max-w-[calc(100vw-2rem)]">
				{#if $mobile && active}
					<button type="button" aria-label={$i18n.t('Back')} on:click={back}>
						<ChevronLeft className="size-3.5" />
						<span>{active.control.label}</span>
					</button>
					{@render choices(active.model, active.key, active.control)}
				{:else}
					{#each available as model (model.id)}
						{#if selectedModels.length > 1}
							<div class="truncate px-2 pt-1.5 pb-0.5 text-xs text-gray-400 dark:text-gray-500">
								{resolveLocalizedModelName(model, $i18n.language)}
							</div>
						{/if}
						{#each Object.entries(localizeModelControls(model, $i18n.language)) as [key, control] (key)}
							{#if control.display === 'slider'}
								<ModelControlSlider
									{control}
									value={modelControls[model.id]?.[key] ?? ''}
									disabled={saving}
									on:change={(event) => select(model.id, key, event.detail)}
								/>
							{:else if $mobile}
								<button
									type="button"
									aria-label={control.label}
									id={`model-control-${model.id}-${key}`}
									class={rowClass}
									on:click={(event) =>
										(active = { model, key, control, trigger: event.currentTarget })}
								>
									{@render summary(model, key, control)}
								</button>
							{:else}
								<DropdownSub
									maxWidth={240}
									contentClass="w-60 max-h-[calc(100dvh-2rem)] overflow-y-auto scrollbar-thin"
								>
									<button
										slot="trigger"
										type="button"
										aria-label={control.label}
										aria-haspopup="menu"
										class={rowClass}
									>
										{@render summary(model, key, control)}
									</button>
									{@render choices(model, key, control)}
								</DropdownSub>
							{/if}
						{/each}
					{/each}
				{/if}
			</DropdownMenu>
		</div>
	</Dropdown>
{/if}
