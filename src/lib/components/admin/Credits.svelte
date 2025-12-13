<script>
	import { getContext, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	dayjs.extend(relativeTime);
	dayjs.extend(localizedFormat);

	import { user } from '$lib/stores';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Pagination from '$lib/components/common/Pagination.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	import {
		getAdminCreditsStats,
		getAdminCreditsUsers,
		getAdminCreditsUser
	} from '$lib/apis/credits';

	const i18n = getContext('i18n');

	let loaded = false;
	let loading = true;

	let stats = null;
	let usersData = null;
	let total = 0;

	let query = '';
	let page = 1;
	let perPage = 50;

	let sortKey = 'audio_remaining';
	let sortDirection = 'desc';

	let showDetails = false;
	let detailsLoading = false;
	let details = null;

	const setSortKey = (key) => {
		if (sortKey === key) {
			sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
		} else {
			sortKey = key;
			sortDirection = 'desc';
		}
	};

	const getRowSortValue = (row, key) => {
		if (!row) return null;
		switch (key) {
			case 'audio_remaining':
				return row?.domains?.audio?.total_remaining ?? null;
			case 'photo_remaining':
				return row?.domains?.photo?.total_remaining ?? null;
			case 'video_remaining':
				return row?.domains?.video?.total_remaining ?? null;
			case 'music_remaining':
				return row?.domains?.music?.total_remaining ?? null;
			case 'total_purchased_credits_audio':
				return row?.total_purchased_credits_audio ?? null;
			case 'total_used_credits_audio':
				return row?.total_used_credits_audio ?? null;
			case 'last_credit_activity_audio':
				return row?.last_credit_activity_audio ?? null;
			case 'email':
				return row?.email ?? '';
			case 'user_id':
			default:
				return row?.user_id ?? '';
		}
	};

	const formatRevenue = (revenueByCurrencyMinor) => {
		if (!revenueByCurrencyMinor) return '--';
		const parts = Object.entries(revenueByCurrencyMinor).map(([currency, minor]) => {
			const amount = typeof minor === 'number' ? (minor / 100).toFixed(2) : `${minor}`;
			return `${currency} ${amount}`;
		});
		return parts.length ? parts.join(' • ') : '--';
	};

	const loadData = async () => {
		loading = true;

		const token = localStorage.token;
		if (!token) {
			loading = false;
			return;
		}

		const [statsRes, usersRes] = await Promise.all([
			getAdminCreditsStats(token).catch((error) => {
				toast.error(`${error}`);
				return null;
			}),
			getAdminCreditsUsers(token, query, page, perPage).catch((error) => {
				toast.error(`${error}`);
				return null;
			})
		]);

		if (statsRes) stats = statsRes;
		if (!stats) {
			stats = {
				redis_available: false,
				total_users: 0,
				domains: {},
				total_purchased_credits_audio: 0,
				total_used_credits_audio: 0,
				total_credits_issued_audio: null,
				total_revenue_by_currency_minor: null
			};
		}
		if (usersRes) {
			usersData = usersRes.users;
			total = usersRes.total;
		}
		if (!usersData) {
			usersData = [];
			total = 0;
		}

		loading = false;
	};

	const openDetails = async (userId) => {
		showDetails = true;
		detailsLoading = true;
		details = null;

		const token = localStorage.token;
		if (!token) {
			detailsLoading = false;
			return;
		}

		const res = await getAdminCreditsUser(token, userId).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) details = res;
		detailsLoading = false;
	};

	const closeDetails = () => {
		showDetails = false;
		details = null;
	};

	$: sortedUsers =
		usersData === null
			? []
			: [...usersData].sort((a, b) => {
					const dir = sortDirection === 'asc' ? 1 : -1;

					const av = getRowSortValue(a, sortKey);
					const bv = getRowSortValue(b, sortKey);

					if (typeof av === 'string' || typeof bv === 'string') {
						const as = `${av ?? ''}`;
						const bs = `${bv ?? ''}`;
						return as.localeCompare(bs) * dir;
					}

					if (av === null && bv === null) return 0;
					if (av === null) return 1;
					if (bv === null) return -1;

					return (Number(av) - Number(bv)) * dir;
				});

	$: if (loaded) {
		query;
		page;
		perPage;
		loadData();
	}

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
			return;
		}

		loaded = true;
	});
</script>

{#if !loaded || usersData === null || stats === null}
	<div class="my-10">
		<Spinner className="size-5" />
	</div>
{:else}
	<div
		class="pt-0.5 pb-2 gap-2 flex flex-col md:flex-row justify-between sticky top-0 z-10 bg-white dark:bg-gray-900"
	>
		<div class="flex md:self-center text-lg font-medium px-0.5 gap-2">
			<div class="flex-shrink-0">{$i18n.t('Credits')}</div>
		</div>

		<div class="flex gap-2">
			<div class="flex flex-1">
				<div class="self-center ml-1 mr-3">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
						<path
							fill-rule="evenodd"
							d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
				<input
					class="w-full text-sm pr-4 py-1 rounded-r-xl outline-hidden bg-transparent"
					bind:value={query}
					placeholder={$i18n.t('Search')}
				/>
			</div>

			<Tooltip content={$i18n.t('Refresh')}>
				<button
					class="p-2 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition font-medium text-sm"
					on:click={() => loadData()}
					disabled={loading}
				>
					{#if loading}
						<Spinner className="size-4" />
					{:else}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path
								fill-rule="evenodd"
								d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.002-.001a.75.75 0 00-1.063 1.06l.003.003a7 7 0 0011.2-3.765.75.75 0 00-1.437-.263zM4.688 8.576a5.5 5.5 0 019.201-2.466l.002.001a.75.75 0 001.063-1.06l-.003-.003a7 7 0 00-11.2 3.765.75.75 0 001.437.263z"
								clip-rule="evenodd"
							/>
						</svg>
					{/if}
				</button>
			</Tooltip>
		</div>
	</div>

	{#if stats && !stats.redis_available}
		<div class="mb-2 text-xs rounded-lg border border-gray-200 dark:border-gray-800 p-2 text-gray-600 dark:text-gray-300">
			{$i18n.t('Credits disabled (Redis unavailable).')}
		</div>
	{/if}

	<div class="grid grid-cols-2 lg:grid-cols-5 gap-2 mb-3">
		<div class="p-3 rounded-xl border border-gray-100 dark:border-gray-850/60">
			<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Total users')}</div>
			<div class="text-lg font-medium text-gray-900 dark:text-gray-100">{stats.total_users}</div>
		</div>

		<div class="p-3 rounded-xl border border-gray-100 dark:border-gray-850/60">
			<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Audio remaining')}</div>
			<div class="text-lg font-medium text-gray-900 dark:text-gray-100">
				{stats?.domains?.audio?.total_remaining ?? '--'}
			</div>
		</div>

		<div class="p-3 rounded-xl border border-gray-100 dark:border-gray-850/60">
			<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Photo remaining')}</div>
			<div class="text-lg font-medium text-gray-900 dark:text-gray-100">
				{stats?.domains?.photo?.total_remaining ?? '--'}
			</div>
		</div>

		<div class="p-3 rounded-xl border border-gray-100 dark:border-gray-850/60">
			<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Video remaining')}</div>
			<div class="text-lg font-medium text-gray-900 dark:text-gray-100">
				{stats?.domains?.video?.total_remaining ?? '--'}
			</div>
		</div>

		<div class="p-3 rounded-xl border border-gray-100 dark:border-gray-850/60">
			<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Music remaining')}</div>
			<div class="text-lg font-medium text-gray-900 dark:text-gray-100">
				{stats?.domains?.music?.total_remaining ?? '--'}
			</div>
		</div>
	</div>

	<div class="grid grid-cols-2 lg:grid-cols-4 gap-2 mb-3">
		<div class="p-3 rounded-xl border border-gray-100 dark:border-gray-850/60">
			<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Audio credits issued')}</div>
			<div class="text-lg font-medium text-gray-900 dark:text-gray-100">
				{stats.total_credits_issued_audio ?? '--'}
			</div>
		</div>

		<div class="p-3 rounded-xl border border-gray-100 dark:border-gray-850/60">
			<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Audio credits spent')}</div>
			<div class="text-lg font-medium text-gray-900 dark:text-gray-100">
				{stats.total_used_credits_audio}
			</div>
		</div>

		<div class="p-3 rounded-xl border border-gray-100 dark:border-gray-850/60">
			<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Audio credits purchased')}</div>
			<div class="text-lg font-medium text-gray-900 dark:text-gray-100">
				{stats.total_purchased_credits_audio}
			</div>
		</div>

		<div class="p-3 rounded-xl border border-gray-100 dark:border-gray-850/60">
			<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Total revenue')}</div>
			<div class="text-sm font-medium text-gray-900 dark:text-gray-100">
				{formatRevenue(stats.total_revenue_by_currency_minor)}
			</div>
		</div>
	</div>

	<div class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full">
		<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full">
			<thead class="text-xs text-gray-800 uppercase bg-transparent dark:text-gray-200">
				<tr class="border-b-[1.5px] border-gray-50 dark:border-gray-850/30">
					<th
						scope="col"
						class="px-2.5 py-2 cursor-pointer select-none"
						on:click={() => setSortKey('user_id')}
					>
						{$i18n.t('User ID')}
					</th>
					<th
						scope="col"
						class="px-2.5 py-2 cursor-pointer select-none"
						on:click={() => setSortKey('email')}
					>
						{$i18n.t('Email / Username')}
					</th>
					<th
						scope="col"
						class="px-2.5 py-2 cursor-pointer select-none"
						on:click={() => setSortKey('audio_remaining')}
					>
						{$i18n.t('Audio')}
					</th>
					<th
						scope="col"
						class="px-2.5 py-2 cursor-pointer select-none"
						on:click={() => setSortKey('photo_remaining')}
					>
						{$i18n.t('Photo')}
					</th>
					<th
						scope="col"
						class="px-2.5 py-2 cursor-pointer select-none"
						on:click={() => setSortKey('video_remaining')}
					>
						{$i18n.t('Video')}
					</th>
					<th
						scope="col"
						class="px-2.5 py-2 cursor-pointer select-none"
						on:click={() => setSortKey('music_remaining')}
					>
						{$i18n.t('Music')}
					</th>
					<th
						scope="col"
						class="px-2.5 py-2 cursor-pointer select-none"
						on:click={() => setSortKey('total_purchased_credits_audio')}
					>
						{$i18n.t('Audio purchased')}
					</th>
					<th
						scope="col"
						class="px-2.5 py-2 cursor-pointer select-none"
						on:click={() => setSortKey('total_used_credits_audio')}
					>
						{$i18n.t('Audio used')}
					</th>
					<th
						scope="col"
						class="px-2.5 py-2 cursor-pointer select-none"
						on:click={() => setSortKey('last_credit_activity_audio')}
					>
						{$i18n.t('Last audio activity')}
					</th>
					<th scope="col" class="px-2.5 py-2"></th>
				</tr>
			</thead>
			<tbody>
				{#each sortedUsers as row (row.user_id)}
					<tr class="border-b border-gray-50 dark:border-gray-850/30">
						<td class="px-2.5 py-2 font-mono text-xs text-gray-700 dark:text-gray-300">
							{row.user_id}
						</td>
						<td class="px-2.5 py-2">
							<div class="text-gray-800 dark:text-gray-100">{row.email ?? '--'}</div>
							<div class="text-xs text-gray-400 dark:text-gray-500">{row.username ?? ''}</div>
						</td>
						<td class="px-2.5 py-2 text-gray-800 dark:text-gray-100">
							{row?.domains?.audio?.total_remaining ?? '--'}
						</td>
						<td class="px-2.5 py-2 text-gray-800 dark:text-gray-100">
							{row?.domains?.photo?.total_remaining ?? '--'}
						</td>
						<td class="px-2.5 py-2 text-gray-800 dark:text-gray-100">
							{row?.domains?.video?.total_remaining ?? '--'}
						</td>
						<td class="px-2.5 py-2 text-gray-800 dark:text-gray-100">
							{row?.domains?.music?.total_remaining ?? '--'}
						</td>
						<td class="px-2.5 py-2 text-gray-800 dark:text-gray-100">
							{row.total_purchased_credits_audio}
						</td>
						<td class="px-2.5 py-2 text-gray-800 dark:text-gray-100">
							{row.total_used_credits_audio}
						</td>
						<td class="px-2.5 py-2">
							{#if row.last_credit_activity_audio}
								<Tooltip content={dayjs.unix(row.last_credit_activity_audio).format('lll')}>
									<span class="text-gray-800 dark:text-gray-100">
										{dayjs.unix(row.last_credit_activity_audio).fromNow()}
									</span>
								</Tooltip>
							{:else}
								<span class="text-gray-400">--</span>
							{/if}
						</td>
						<td class="px-2.5 py-2 text-right">
							<button
								class="text-xs px-2 py-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition text-gray-700 dark:text-gray-200"
								on:click={() => openDetails(row.user_id)}
							>
								{$i18n.t('Details')}
							</button>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	{#if total > perPage}
		<Pagination bind:page count={total} perPage={perPage} />
	{/if}
{/if}

{#if showDetails}
	<div
		class="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4"
		on:click|self={closeDetails}
	>
		<div class="w-full max-w-3xl max-h-[85vh] overflow-y-auto rounded-xl bg-white dark:bg-gray-900 p-4">
			<div class="flex items-center justify-between gap-2 mb-3">
				<div class="text-lg font-medium text-gray-900 dark:text-gray-100">
					{$i18n.t('Credits')}{#if details?.user?.email} ({details.user.email}){/if}
				</div>
				<button
					class="text-xs px-2 py-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition text-gray-700 dark:text-gray-200"
					on:click={closeDetails}
				>
					{$i18n.t('Close')}
				</button>
			</div>

			{#if detailsLoading}
				<div class="my-8">
					<Spinner className="size-5" />
				</div>
			{:else if details}
				<div class="grid grid-cols-2 lg:grid-cols-4 gap-2 mb-3">
					{#each ['audio', 'photo', 'video', 'music'] as domain (domain)}
						{@const d = details?.domains?.[domain]}
						<div class="p-3 rounded-xl border border-gray-100 dark:border-gray-850/60">
							<div class="text-xs text-gray-500 dark:text-gray-400">{domain}</div>
							<div class="mt-1 text-sm font-medium text-gray-900 dark:text-gray-100">
								{$i18n.t('Free')}: {d?.free_remaining ?? '--'} / {d?.free_limit ?? '--'}
							</div>
							<div class="mt-1 text-xs text-gray-600 dark:text-gray-300">
								{$i18n.t('Paid')}: {d?.paid_balance ?? '--'} · {$i18n.t('Total')}:{' '}
								{d?.total_remaining ?? '--'}
							</div>
						</div>
					{/each}
				</div>

				<div class="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
					{$i18n.t('Audio Purchases')}
				</div>

				{#if details.purchases_audio?.length}
					<div class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full">
						<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full">
							<thead class="text-xs text-gray-800 uppercase bg-transparent dark:text-gray-200">
								<tr class="border-b-[1.5px] border-gray-50 dark:border-gray-850/30">
									<th scope="col" class="px-2.5 py-2">{$i18n.t('Purchase ID')}</th>
									<th scope="col" class="px-2.5 py-2">{$i18n.t('Credits')}</th>
									<th scope="col" class="px-2.5 py-2">{$i18n.t('Price')}</th>
									<th scope="col" class="px-2.5 py-2">{$i18n.t('Currency')}</th>
									<th scope="col" class="px-2.5 py-2">{$i18n.t('Provider')}</th>
									<th scope="col" class="px-2.5 py-2">{$i18n.t('Date')}</th>
									<th scope="col" class="px-2.5 py-2">{$i18n.t('Status')}</th>
								</tr>
							</thead>
							<tbody>
								{#each details.purchases_audio as p (p.purchase_id)}
									<tr class="border-b border-gray-50 dark:border-gray-850/30">
										<td class="px-2.5 py-2 font-mono text-xs text-gray-700 dark:text-gray-300">
											{p.purchase_id}
										</td>
										<td class="px-2.5 py-2 text-gray-800 dark:text-gray-100">{p.credits}</td>
										<td class="px-2.5 py-2 text-gray-800 dark:text-gray-100">
											{#if p.price_minor != null}
												{(p.price_minor / 100).toFixed(2)}
											{:else}
												--
											{/if}
										</td>
										<td class="px-2.5 py-2 text-gray-800 dark:text-gray-100">{p.currency ?? '--'}</td>
										<td class="px-2.5 py-2 text-gray-800 dark:text-gray-100">
											{p.payment_provider ?? '--'}
										</td>
										<td class="px-2.5 py-2 text-gray-800 dark:text-gray-100">
											{dayjs.unix(p.purchase_date).format('lll')}
										</td>
										<td class="px-2.5 py-2 text-gray-800 dark:text-gray-100">{p.status ?? '--'}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{:else}
					<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('No purchases found.')}</div>
				{/if}
			{/if}
		</div>
	</div>
{/if}
