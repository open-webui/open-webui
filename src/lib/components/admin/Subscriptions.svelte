<script>
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	import { models } from '$lib/stores';
	import { getAdminTiers, upsertTier, deleteTier, seedTiers } from '$lib/apis/subscriptions';

	let loading = true;
	let savingId = null;
	let tiers = [];
	let newCounter = 0;

	const blankTier = () => ({
		id: '',
		name: '',
		description: '',
		price_usd: 0,
		duration_days: 30,
		daily_message_limit: 10,
		allowed_model_ids: [],
		enabled: true,
		sort_order: tiers.length,
		_isNew: true,
		_uid: `new-${++newCounter}`
	});

	const load = async () => {
		loading = true;
		tiers = (await getAdminTiers(localStorage.token).catch(() => [])) ?? [];
		tiers = tiers.map((t) => ({ ...t, allowed_model_ids: t.allowed_model_ids ?? [], _uid: t.id }));
		loading = false;
	};

	const addTier = () => {
		tiers = [...tiers, blankTier()];
	};

	const seed = async () => {
		await seedTiers(localStorage.token).catch((e) => toast.error(`${e}`));
		await load();
		toast.success($i18n.t('Default plans created'));
	};

	const isUnlimited = (tier) => tier.daily_message_limit === null || tier.daily_message_limit === undefined;

	const toggleUnlimited = (tier) => {
		tier.daily_message_limit = isUnlimited(tier) ? 10 : null;
		tiers = tiers;
	};

	const toggleModel = (tier, modelId) => {
		const set = new Set(tier.allowed_model_ids ?? []);
		if (set.has(modelId)) set.delete(modelId);
		else set.add(modelId);
		tier.allowed_model_ids = Array.from(set);
		tiers = tiers;
	};

	const save = async (tier) => {
		const id = (tier.id ?? '').trim().toLowerCase();
		if (!id) {
			toast.error($i18n.t('Plan id is required (e.g. pro)'));
			return;
		}
		savingId = id;
		try {
			const payload = {
				id,
				name: tier.name || id,
				description: tier.description ?? '',
				price_usd: Number(tier.price_usd) || 0,
				duration_days: Number(tier.duration_days) || 30,
				daily_message_limit: isUnlimited(tier) ? null : Number(tier.daily_message_limit),
				allowed_model_ids: tier.allowed_model_ids ?? [],
				enabled: !!tier.enabled,
				sort_order: Number(tier.sort_order) || 0
			};
			await upsertTier(localStorage.token, payload);
			toast.success($i18n.t('Plan saved'));
			await load();
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			savingId = null;
		}
	};

	const remove = async (tier) => {
		if (tier._isNew) {
			tiers = tiers.filter((t) => t !== tier);
			return;
		}
		if (tier.id === 'free') {
			toast.error($i18n.t('The default free plan cannot be deleted'));
			return;
		}
		if (!confirm($i18n.t('Delete plan "{{name}}"?', { name: tier.name || tier.id }))) return;
		try {
			await deleteTier(localStorage.token, tier.id);
			toast.success($i18n.t('Plan deleted'));
			await load();
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	onMount(load);
</script>

<div class="px-4 md:px-8 py-6 max-w-4xl mx-auto w-full">
	<div class="flex items-center justify-between mb-1">
		<div class="text-lg font-medium">{$i18n.t('Subscription Plans')}</div>
		<div class="flex gap-2">
			{#if tiers.length === 0 && !loading}
				<button
					class="px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-800 text-sm font-medium"
					on:click={seed}
				>
					{$i18n.t('Create defaults')}
				</button>
			{/if}
			<button
				class="px-3 py-1.5 rounded-lg bg-black text-white dark:bg-white dark:text-black text-sm font-medium"
				on:click={addTier}
			>
				{$i18n.t('Add plan')}
			</button>
		</div>
	</div>
	<div class="text-xs text-gray-500 mb-4">
		{$i18n.t(
			'Configure price (USDT), duration, daily message limit and allowed models per tier. The model backend is KyberRouter. An empty model list means all models are allowed.'
		)}
	</div>

	{#if loading}
		<div class="text-sm text-gray-500 py-8 text-center">{$i18n.t('Loading…')}</div>
	{:else}
		<div class="space-y-4">
			{#each tiers as tier (tier._uid)}
				<div class="rounded-2xl border border-gray-100 dark:border-gray-800 p-4">
					<div class="flex items-center justify-between gap-2 mb-3">
						<div class="flex items-center gap-2">
							<input
								class="w-24 px-2 py-1 rounded-md bg-gray-50 dark:bg-gray-850 border border-gray-100 dark:border-gray-800 text-sm font-mono outline-none"
								placeholder={$i18n.t('id')}
								bind:value={tier.id}
								disabled={!tier._isNew}
							/>
							<input
								class="px-2 py-1 rounded-md bg-gray-50 dark:bg-gray-850 border border-gray-100 dark:border-gray-800 text-sm font-medium outline-none"
								placeholder={$i18n.t('Display name')}
								bind:value={tier.name}
							/>
						</div>
						<label class="flex items-center gap-1.5 text-xs text-gray-500 select-none">
							<input type="checkbox" bind:checked={tier.enabled} />
							{$i18n.t('Enabled')}
						</label>
					</div>

					<div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
						<label class="flex flex-col gap-1 text-xs text-gray-500">
							{$i18n.t('Price (USDT)')}
							<input
								type="number"
								min="0"
								step="0.01"
								class="px-2 py-1 rounded-md bg-gray-50 dark:bg-gray-850 border border-gray-100 dark:border-gray-800 text-sm text-black dark:text-white outline-none"
								bind:value={tier.price_usd}
							/>
						</label>
						<label class="flex flex-col gap-1 text-xs text-gray-500">
							{$i18n.t('Duration (days)')}
							<input
								type="number"
								min="1"
								class="px-2 py-1 rounded-md bg-gray-50 dark:bg-gray-850 border border-gray-100 dark:border-gray-800 text-sm text-black dark:text-white outline-none"
								bind:value={tier.duration_days}
							/>
						</label>
						<label class="flex flex-col gap-1 text-xs text-gray-500">
							{$i18n.t('Daily messages')}
							<input
								type="number"
								min="0"
								class="px-2 py-1 rounded-md bg-gray-50 dark:bg-gray-850 border border-gray-100 dark:border-gray-800 text-sm text-black dark:text-white outline-none disabled:opacity-40"
								bind:value={tier.daily_message_limit}
								disabled={isUnlimited(tier)}
							/>
						</label>
						<label class="flex items-end gap-1.5 text-xs text-gray-500 select-none pb-1">
							<input type="checkbox" checked={isUnlimited(tier)} on:change={() => toggleUnlimited(tier)} />
							{$i18n.t('Unlimited')}
						</label>
					</div>

					<label class="flex flex-col gap-1 text-xs text-gray-500 mb-3">
						{$i18n.t('Description')}
						<input
							class="px-2 py-1 rounded-md bg-gray-50 dark:bg-gray-850 border border-gray-100 dark:border-gray-800 text-sm text-black dark:text-white outline-none"
							bind:value={tier.description}
						/>
					</label>

					<div class="text-xs text-gray-500 mb-1">
						{$i18n.t('Allowed models')}
						<span class="text-gray-400">
							({tier.allowed_model_ids?.length
								? $i18n.t('{{count}} selected', { count: tier.allowed_model_ids.length })
								: $i18n.t('all models')})
						</span>
					</div>
					<div
						class="max-h-40 overflow-y-auto rounded-md border border-gray-100 dark:border-gray-800 p-2 mb-3 grid grid-cols-1 sm:grid-cols-2 gap-1"
					>
						{#if ($models ?? []).length === 0}
							<div class="text-xs text-gray-400">{$i18n.t('No models loaded.')}</div>
						{:else}
							{#each $models.filter((m) => m?.id) as m (m.id)}
								<label class="flex items-center gap-1.5 text-xs truncate">
									<input
										type="checkbox"
										checked={(tier.allowed_model_ids ?? []).includes(m.id)}
										on:change={() => toggleModel(tier, m.id)}
									/>
									<span class="truncate">{m.name ?? m.id}</span>
								</label>
							{/each}
						{/if}
					</div>

					<div class="flex items-center justify-between">
						<button
							class="text-xs text-red-500 hover:underline"
							on:click={() => remove(tier)}
						>
							{$i18n.t('Delete')}
						</button>
						<button
							class="px-4 py-1.5 rounded-lg bg-black text-white dark:bg-white dark:text-black text-sm font-medium disabled:opacity-50"
							on:click={() => save(tier)}
							disabled={savingId === tier.id}
						>
							{savingId === tier.id ? $i18n.t('Saving…') : $i18n.t('Save')}
						</button>
					</div>
				</div>
			{/each}

			{#if tiers.length === 0}
				<div class="text-center text-sm text-gray-500 py-10">
					{$i18n.t('No plans yet. Create the defaults or add one.')}
				</div>
			{/if}
		</div>
	{/if}
</div>
