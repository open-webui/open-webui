<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import localizedFormat from 'dayjs/plugin/localizedFormat';

	import { models, WEBUI_NAME, showSidebar } from '$lib/stores';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	import {
		updateAutomationById,
		toggleAutomationById,
		runAutomationById,
		deleteAutomationById,
		getAutomationRuns,
		type AutomationForm,
		type AutomationResponse,
		type AutomationRunModel
	} from '$lib/apis/automations';
	import { getTerminalServers, type TerminalServer } from '$lib/apis/terminal/index';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import Cloud from '$lib/components/icons/Cloud.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';

	dayjs.extend(relativeTime);
	dayjs.extend(localizedFormat);

	const i18n = getContext('i18n');

	export let automation: AutomationResponse;

	let name = '';
	let prompt = '';
	let model_id = '';
	let is_active = true;

	let frequency = 'DAILY';
	let interval = 1;
	let hour = 9;
	let minute = 0;
	let selectedDays: string[] = [];
	let monthDay = 1;
	let onceDate = '';
	let onceTime = '09:00';
	let customRrule = '';

	let terminalServers: TerminalServer[] = [];
	let terminalServerId = '';
	let terminalCwd = '';

	let loading = false;
	let saving = false;
	let showDeleteConfirm = false;
	let showScheduleDropdown = false;
	let showModelDropdown = false;
	let showTerminalDropdown = false;
	let modelSearch = '';

	let runs: AutomationRunModel[] = [];
	let runsLoading = false;
	let isDirty = false;

	$: terminalLabel = terminalServerId
		? terminalServers.find((s) => s.id === terminalServerId)?.name || 'Terminal'
		: $i18n.t('None');

	$: modelLabel = model_id
		? $models.find((m) => m.id === model_id)?.name || model_id
		: $i18n.t('Select model');

	$: filteredModels = modelSearch
		? $models.filter(
				(m) =>
					m.name.toLowerCase().includes(modelSearch.toLowerCase()) ||
					m.id.toLowerCase().includes(modelSearch.toLowerCase())
			)
		: $models;

	const FREQUENCIES = [
		{ key: 'ONCE', label: 'Once' },
		{ key: 'HOURLY', label: 'Hourly' },
		{ key: 'DAILY', label: 'Daily' },
		{ key: 'WEEKLY', label: 'Weekly' },
		{ key: 'MONTHLY', label: 'Monthly' },
		{ key: 'CUSTOM', label: 'Custom' }
	];

	const DAYS = [
		{ key: 'MO', label: 'Mo' },
		{ key: 'TU', label: 'Tu' },
		{ key: 'WE', label: 'We' },
		{ key: 'TH', label: 'Th' },
		{ key: 'FR', label: 'Fr' },
		{ key: 'SA', label: 'Sa' },
		{ key: 'SU', label: 'Su' }
	];

	let lastVisualFrequency = 'DAILY';
	let prevFrequency = 'DAILY';

	$: if (frequency !== 'CUSTOM') {
		lastVisualFrequency = frequency;
	}

	$: if (frequency === 'ONCE' && !onceDate) {
		const soon = new Date(Date.now() + 5 * 60_000);
		onceDate = soon.toISOString().split('T')[0];
		onceTime = `${String(soon.getHours()).padStart(2, '0')}:${String(soon.getMinutes()).padStart(2, '0')}`;
	}

	$: {
		if (frequency === 'CUSTOM' && prevFrequency !== 'CUSTOM') {
			customRrule = buildVisualRrule();
		}
		prevFrequency = frequency;
	}

	const buildVisualRrule = (): string => {
		if (lastVisualFrequency === 'ONCE') {
			const dt = onceDate.replace(/-/g, '') + 'T' + onceTime.replace(/:/g, '') + '00';
			return `DTSTART:${dt}\nRRULE:FREQ=DAILY;COUNT=1`;
		}
		let parts = [`FREQ=${lastVisualFrequency}`];
		if (interval > 1) parts.push(`INTERVAL=${interval}`);
		if (lastVisualFrequency === 'WEEKLY' && selectedDays.length)
			parts.push(`BYDAY=${selectedDays.join(',')}`);
		if (lastVisualFrequency === 'MONTHLY') parts.push(`BYMONTHDAY=${monthDay}`);
		if (['DAILY', 'WEEKLY', 'MONTHLY'].includes(lastVisualFrequency)) parts.push(`BYHOUR=${hour}`);
		parts.push(`BYMINUTE=${minute}`);
		return `RRULE:${parts.join(';')}`;
	};

	const buildRrule = (): string => {
		if (frequency === 'CUSTOM') return customRrule;
		if (frequency === 'ONCE') {
			const dt = onceDate.replace(/-/g, '') + 'T' + onceTime.replace(/:/g, '') + '00';
			return `DTSTART:${dt}\nRRULE:FREQ=DAILY;COUNT=1`;
		}
		let parts = [`FREQ=${frequency}`];
		if (interval > 1) parts.push(`INTERVAL=${interval}`);
		if (frequency === 'WEEKLY' && selectedDays.length)
			parts.push(`BYDAY=${selectedDays.join(',')}`);
		if (frequency === 'MONTHLY') parts.push(`BYMONTHDAY=${monthDay}`);
		if (['DAILY', 'WEEKLY', 'MONTHLY'].includes(frequency)) parts.push(`BYHOUR=${hour}`);
		parts.push(`BYMINUTE=${minute}`);
		return `RRULE:${parts.join(';')}`;
	};

	const parseRrule = (s: string) => {
		if (s.includes('COUNT=1')) {
			frequency = 'ONCE';
			const match = s.match(/DTSTART:(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})/);
			if (match) {
				onceDate = `${match[1]}-${match[2]}-${match[3]}`;
				onceTime = `${match[4]}:${match[5]}`;
			}
			return;
		}
		const parts: Record<string, string> = {};
		s.replace('RRULE:', '')
			.split(';')
			.forEach((p) => {
				const [k, v] = p.split('=');
				if (k && v) parts[k] = v;
			});
		const freq = parts.FREQ || 'DAILY';
		if (!['HOURLY', 'DAILY', 'WEEKLY', 'MONTHLY'].includes(freq)) {
			frequency = 'CUSTOM';
			customRrule = s;
			return;
		}
		frequency = freq;
		interval = parseInt(parts.INTERVAL || '1');
		hour = parseInt(parts.BYHOUR || '9');
		minute = parseInt(parts.BYMINUTE || '0');
		selectedDays = parts.BYDAY ? parts.BYDAY.split(',') : [];
		monthDay = parseInt(parts.BYMONTHDAY || '1');
	};

	$: scheduleLabel = (() => {
		if (frequency === 'ONCE') return 'Once';
		if (frequency === 'HOURLY') return interval > 1 ? `Every ${interval}h` : 'Hourly';
		if (frequency === 'DAILY') {
			const ampm = hour >= 12 ? 'PM' : 'AM';
			const h12 = hour % 12 || 12;
			return `Daily at ${h12}:${String(minute).padStart(2, '0')} ${ampm}`;
		}
		if (frequency === 'WEEKLY') return 'Weekly';
		if (frequency === 'MONTHLY') return 'Monthly';
		if (frequency === 'CUSTOM') return 'Custom';
		return 'Schedule';
	})();

	const formatRunTime = (ts: number): string => {
		const now = Date.now();
		const diff = now - ts / 1_000_000;

		const seconds = Math.floor(diff / 1000);
		const minutes = Math.floor(seconds / 60);
		const hours = Math.floor(minutes / 60);
		const days = Math.floor(hours / 24);
		const weeks = Math.floor(days / 7);
		const years = Math.floor(days / 365);

		if (years > 0) return $i18n.t('{{COUNT}}y', { COUNT: years, context: 'time_ago' });
		if (weeks > 0) return $i18n.t('{{COUNT}}w', { COUNT: weeks, context: 'time_ago' });
		if (days > 0) return $i18n.t('{{COUNT}}d', { COUNT: days, context: 'time_ago' });
		if (hours > 0) return $i18n.t('{{COUNT}}h', { COUNT: hours, context: 'time_ago' });
		if (minutes > 0) return $i18n.t('{{COUNT}}m', { COUNT: minutes, context: 'time_ago' });
		return $i18n.t('1m', { context: 'time_ago' });
	};

	const formatNextRun = (ts: number | null): string => {
		if (!ts) return $i18n.t('Not scheduled');
		const d = dayjs(ts / 1_000_000);
		if (d.isSame(dayjs(), 'day')) return `${$i18n.t('Today at')} ${d.format('LT')}`;
		return d.format('L LT');
	};

	const saveHandler = async () => {
		if (!name.trim() || !prompt.trim() || !model_id.trim()) {
			toast.error($i18n.t('Name, prompt, and model are required'));
			return;
		}
		saving = true;
		try {
			const form: AutomationForm = {
				name: name.trim(),
				data: {
					prompt: prompt.trim(),
					model_id: model_id.trim(),
					rrule: buildRrule(),
					...(terminalServerId
						? {
								terminal: {
									server_id: terminalServerId,
									...(terminalCwd.trim() ? { cwd: terminalCwd.trim() } : {})
								}
							}
						: {})
				},
				is_active
			};
			const updated = await updateAutomationById(localStorage.token, automation.id, form);
			if (updated) {
				automation = updated;
				isDirty = false;
				toast.success($i18n.t('Automation updated'));
			}
		} catch (e: any) {
			toast.error(e?.detail ?? `${e}` ?? 'Failed to save');
		} finally {
			saving = false;
		}
	};

	const toggleHandler = async () => {
		const res = await toggleAutomationById(localStorage.token, automation.id).catch((err) => {
			toast.error(`${err}`);
			return null;
		});
		if (res) {
			is_active = res.is_active;
			automation = res;
		}
	};

	const runNowHandler = async () => {
		loading = true;
		const res = await runAutomationById(localStorage.token, automation.id).catch((err) => {
			toast.error(`${err}`);
			return null;
		});
		if (res) {
			toast.success($i18n.t('Automation triggered'));
			setTimeout(loadRuns, 2000);
		}
		loading = false;
	};

	const deleteHandler = async () => {
		const res = await deleteAutomationById(localStorage.token, automation.id).catch((err) => {
			toast.error(`${err}`);
			return null;
		});
		if (res) {
			toast.success($i18n.t(`Deleted {{name}}`, { name: automation.name }));
			goto('/automations');
		}
	};

	const loadRuns = async () => {
		runsLoading = true;
		try {
			runs = (await getAutomationRuns(localStorage.token, automation.id, 0, 50)) ?? [];
		} catch {
			runs = [];
		}
		runsLoading = false;
	};

	const markDirty = () => {
		isDirty = true;
	};

	onMount(async () => {
		name = automation.name;
		prompt = automation.data.prompt;
		model_id = automation.data.model_id;
		is_active = automation.is_active;
		parseRrule(automation.data.rrule);
		terminalServerId = automation.data.terminal?.server_id || '';
		terminalCwd = automation.data.terminal?.cwd || '';

		try {
			terminalServers = await getTerminalServers(localStorage.token);
		} catch {
			terminalServers = [];
		}
		await loadRuns();
	});
</script>

<svelte:head>
	<title>{name || $i18n.t('Automation')} • {$WEBUI_NAME}</title>
</svelte:head>

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete automation?')}
	on:confirm={deleteHandler}
>
	<div class="text-sm text-gray-500 truncate">
		{$i18n.t('This will delete')} <span class="">{automation.name}</span>.
	</div>
</DeleteConfirmDialog>

<div
	class="flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''} max-w-full"
>
	<div class="flex-1 max-h-full flex flex-col pt-3 pb-1 px-3 md:px-[18px]">
		<!-- Header Segment (Shrink-0 so it doesn't compress) -->
		<div class="flex items-start justify-between gap-4 shrink-0 mb-0.5">
			<div class="flex-1 min-w-0">
				<div class="flex items-center gap-1.5 mb-1.5">
					<Tooltip content={$i18n.t('Back')}>
						<button
							class="text-sm p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg transition"
							aria-label={$i18n.t('Back')}
							on:click={() => goto('/automations')}
							type="button"
						>
							<ChevronLeft strokeWidth="2.5" />
						</button>
					</Tooltip>
					<input
						class="text-2xl w-full bg-transparent outline-hidden"
						placeholder={$i18n.t('Automation Name')}
						bind:value={name}
						on:input={markDirty}
					/>
				</div>
			</div>

			<div class="flex items-center gap-2 shrink-0">
				<Tooltip content={$i18n.t('Delete')}>
					<button
						class="p-2 rounded-full bg-transparent hover:bg-gray-50 dark:hover:bg-gray-850 text-gray-500 hover:text-black dark:hover:text-white transition"
						on:click={() => (showDeleteConfirm = true)}
						type="button"
					>
						<GarbageBin />
					</button>
				</Tooltip>

				{#if isDirty}
					<button
						class="px-4 py-1.5 text-sm bg-black text-white dark:bg-white dark:text-black rounded-full hover:opacity-90 transition flex items-center gap-1.5"
						on:click={saveHandler}
						disabled={saving}
						type="button"
					>
						{$i18n.t('Save')}
						{#if saving}
							<Spinner className="size-3" />
						{/if}
					</button>
				{/if}

				<button
					class="px-4 py-1.5 text-sm border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-850 transition rounded-full flex items-center gap-1.5"
					on:click={runNowHandler}
					type="button"
					disabled={loading}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="size-3.5"
					>
						<path
							d="M6.3 2.84A1.5 1.5 0 0 0 4 4.11v11.78a1.5 1.5 0 0 0 2.3 1.27l9.344-5.891a1.5 1.5 0 0 0 0-2.538L6.3 2.841Z"
						/>
					</svg>
					<div class="hidden md:block">{$i18n.t('Run now')}</div>
					{#if loading}
						<Spinner className="size-3" />
					{/if}
				</button>
			</div>
		</div>

		<!-- Content Segment: Independent Scrolling Columns based on PromptEditor -->
		<div class="flex flex-col md:flex-row gap-4 flex-1 overflow-hidden pb-2 px-1">
			<!-- Main Input Column -->
			<div class="flex-1 flex flex-col min-h-0 overflow-hidden">
				<div class="flex items-center justify-between mb-2 shrink-0 px-1">
					<div class="text-gray-500 text-xs">{$i18n.t('Instructions')}</div>
				</div>
				<div class="relative flex-1 min-h-0">
					<div
						class="bg-gray-50 dark:bg-gray-900 rounded-2xl p-4 border border-gray-100/50 dark:border-gray-850/50 h-full"
					>
						<textarea
							class="w-full h-full text-sm bg-transparent outline-hidden resize-none placeholder:text-gray-300 dark:placeholder:text-gray-700"
							bind:value={prompt}
							on:input={markDirty}
							placeholder={$i18n.t('Enter the prompt instructions for this automation...')}
						/>
					</div>
				</div>
			</div>

			<!-- Sidebar Configuration Column -->
			<div class="hidden md:flex w-full md:w-80 shrink-0 overflow-y-auto px-1 flex-col gap-5">
				<div>
					<div class="text-gray-500 text-xs mb-3">{$i18n.t('Configuration')}</div>
					<div class="space-y-2">
						<!-- Schedule -->
						<div class="flex items-center justify-between text-xs">
							<span class="text-gray-600 dark:text-gray-400">{$i18n.t('Repeats')}</span>
							<Dropdown bind:show={showScheduleDropdown} side="bottom" align="end">
								<button
									type="button"
									class="flex items-center gap-1.5 px-3 py-1.5 rounded-2xl text-xs transition text-gray-700 dark:text-gray-300 hover:bg-black/5 dark:hover:bg-white/5 bg-gray-50 dark:bg-gray-850/50 max-w-40 truncate"
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="1.5"
										stroke="currentColor"
										class="size-3.5 text-gray-400 shrink-0"
										><path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
										/></svg
									>
									<span class="truncate">{scheduleLabel}</span>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="2"
										stroke="currentColor"
										class="size-3 text-gray-400 shrink-0"
										><path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="m19.5 8.25-7.5 7.5-7.5-7.5"
										/></svg
									>
								</button>
								<div
									slot="content"
									class="rounded-2xl shadow-lg border border-gray-200 dark:border-gray-800 flex flex-col bg-white dark:bg-gray-850 w-64 p-1"
								>
									<div class="px-2 text-xs text-gray-500 py-1">
										{$i18n.t('Schedule')}
									</div>
									<div class="px-1.5 mt-0.5 mb-2">
										<select
											class="w-full bg-transparent rounded-xl text-xs py-2 px-2 outline-hidden border-none"
											bind:value={frequency}
											on:click={(e) => e.stopPropagation()}
											on:change={markDirty}
										>
											{#each FREQUENCIES as f}<option value={f.key}>{f.label}</option>{/each}
										</select>
									</div>
									{#if frequency === 'CUSTOM'}
										<div class="px-2 pb-2">
											<input
												type="text"
												bind:value={customRrule}
												placeholder="RRULE:FREQ=DAILY;BYHOUR=9;BYMINUTE=0"
												class="w-full bg-transparent outline-hidden text-xs placeholder:text-gray-400 dark:placeholder:text-gray-600"
												on:click={(e) => e.stopPropagation()}
												on:input={markDirty}
											/>
										</div>
									{:else if frequency !== 'HOURLY'}
										<div class="flex gap-2 flex-wrap items-center px-3 pb-2 text-xs">
											{#if frequency === 'ONCE'}
												<input
													type="date"
													bind:value={onceDate}
													min={new Date().toISOString().split('T')[0]}
													class="bg-transparent outline-hidden text-xs dark:color-scheme-dark"
													on:click={(e) => e.stopPropagation()}
													on:input={markDirty}
												/>
												<input
													type="time"
													bind:value={onceTime}
													class="bg-transparent outline-hidden text-xs dark:color-scheme-dark"
													on:click={(e) => e.stopPropagation()}
													on:input={markDirty}
												/>
											{:else}
												<span class="text-xs text-gray-500 mr-0.5">{$i18n.t('Time')}</span>
												<input
													type="time"
													value={`${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`}
													on:input={(e) => {
														const [h, m] = e.currentTarget.value.split(':').map(Number);
														hour = h;
														minute = m;
														markDirty();
													}}
													class="bg-transparent text-center outline-hidden text-xs dark:color-scheme-dark"
													on:click={(e) => e.stopPropagation()}
												/>
											{/if}
											{#if frequency === 'MONTHLY'}
												<span class="text-xs text-gray-500">{$i18n.t('Day')}</span>
												<input
													type="number"
													bind:value={monthDay}
													min={1}
													max={31}
													class="w-8 bg-transparent text-center outline-hidden text-xs"
													on:click={(e) => e.stopPropagation()}
													on:input={markDirty}
												/>
											{/if}
										</div>
										{#if frequency === 'WEEKLY'}
											<div class="flex gap-1 px-2 pb-2">
												{#each DAYS as d}
													<button
														type="button"
														class="flex-1 py-1 text-xs rounded-xl transition {selectedDays.includes(
															d.key
														)
															? 'bg-black dark:bg-white text-white dark:text-black'
															: 'bg-gray-50 dark:bg-gray-800 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'}"
														on:click={() => {
															selectedDays = selectedDays.includes(d.key)
																? selectedDays.filter((x) => x !== d.key)
																: [...selectedDays, d.key];
															markDirty();
														}}
													>
														{d.label}
													</button>
												{/each}
											</div>
										{/if}
									{/if}
								</div>
							</Dropdown>
						</div>

						<!-- Model -->
						<div class="flex items-center justify-between text-xs">
							<span class="text-gray-600 dark:text-gray-400">{$i18n.t('Model')}</span>
							<Dropdown bind:show={showModelDropdown} side="bottom" align="end">
								<button
									type="button"
									class="flex items-center gap-1.5 px-3 py-1.5 rounded-2xl text-xs transition text-gray-700 dark:text-gray-300 hover:bg-black/5 dark:hover:bg-white/5 bg-gray-50 dark:bg-gray-850/50 max-w-40 truncate"
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="1.5"
										stroke="currentColor"
										class="size-3.5 shrink-0 text-gray-400"
										><path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0 2.455 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z"
										/></svg
									>
									<span class="truncate">{modelLabel}</span>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="2"
										stroke="currentColor"
										class="size-3 shrink-0 text-gray-400"
										><path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="m19.5 8.25-7.5 7.5-7.5-7.5"
										/></svg
									>
								</button>
								<div
									slot="content"
									class="rounded-2xl shadow-lg border border-gray-200 dark:border-gray-800 flex flex-col bg-white dark:bg-gray-850 w-72 p-1"
								>
									<div
										class="flex items-center gap-2 px-2.5 py-1.5 border-b border-gray-100 dark:border-gray-800/50 mb-1"
									>
										<Search className="size-3.5 text-gray-400" strokeWidth="2.5" />
										<input
											bind:value={modelSearch}
											class="w-full text-xs bg-transparent outline-hidden"
											placeholder={$i18n.t('Search a model')}
											autocomplete="off"
											on:click={(e) => e.stopPropagation()}
										/>
									</div>
									<div class="overflow-y-auto scrollbar-thin max-h-60 pt-1">
										{#each filteredModels as model (model.id)}
											<button
												class="px-2.5 py-2 rounded-xl w-full text-left text-xs {model_id ===
												model.id
													? 'bg-gray-50 dark:bg-gray-800/60'
													: 'hover:bg-gray-50 dark:hover:bg-gray-800/30'}"
												type="button"
												on:click={() => {
													model_id = model.id;
													showModelDropdown = false;
													modelSearch = '';
													markDirty();
												}}
											>
												<div class="flex items-center text-black dark:text-gray-100 line-clamp-1">
													<img
														src={`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${encodeURIComponent(model.id)}`}
														alt={model?.name ?? model.id}
														class="rounded-full size-5 shrink-0 mr-2"
														loading="lazy"
														on:error={(e) => {
															e.currentTarget.src = '/favicon.png';
														}}
													/>
													<div class="truncate">{model.name}</div>
												</div>
											</button>
										{:else}
											<div class="block px-3 py-2 text-xs text-gray-500">
												{$i18n.t('No results found')}
											</div>
										{/each}
									</div>
								</div>
							</Dropdown>
						</div>

						<!-- Terminal -->
						{#if terminalServers.length > 0}
							<div class="flex items-center justify-between text-xs">
								<span class="text-gray-600 dark:text-gray-400">{$i18n.t('Terminal')}</span>
								<Dropdown bind:show={showTerminalDropdown} side="bottom" align="end">
									<button
										type="button"
										class="flex items-center gap-1.5 px-3 py-1.5 rounded-2xl text-xs transition text-gray-700 dark:text-gray-300 hover:bg-black/5 dark:hover:bg-white/5 bg-gray-50 dark:bg-gray-850/50 max-w-40 truncate"
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
											stroke-width="1.5"
											stroke="currentColor"
											class="size-3.5 shrink-0 text-gray-400"
											><path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M6.75 7.5l3 2.25-3 2.25m4.5 0h3m-9 8.25h13.5A2.25 2.25 0 0021 18V6a2.25 2.25 0 00-2.25-2.25H5.25A2.25 2.25 0 003 6v12a2.25 2.25 0 002.25 2.25z"
											/></svg
										>
										<span class="truncate">{terminalLabel}</span>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
											stroke-width="2"
											stroke="currentColor"
											class="size-3 shrink-0 text-gray-400"
											><path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="m19.5 8.25-7.5 7.5-7.5-7.5"
											/></svg
										>
									</button>
									<div
										slot="content"
										class="rounded-2xl shadow-lg border border-gray-200 dark:border-gray-800 flex flex-col bg-white dark:bg-gray-850 min-w-56 max-w-56 p-1"
									>
										<div class="px-2 text-xs text-gray-500 py-1">
											{$i18n.t('Terminal Setting')}
										</div>
										{#each terminalServers as server (server.id)}
											<button
												class="flex w-full justify-between gap-2 items-center px-3 py-2 text-xs cursor-pointer rounded-xl {terminalServerId ===
												server.id
													? 'bg-gray-50 dark:bg-gray-800/80 '
													: 'hover:bg-gray-50 dark:hover:bg-gray-800/50'}"
												type="button"
												on:click={() => {
													if (terminalServerId === server.id) {
														terminalServerId = '';
														terminalCwd = '';
													} else {
														terminalServerId = server.id;
													}
													showTerminalDropdown = false;
													markDirty();
												}}
											>
												<div class="flex flex-1 gap-2 items-center truncate">
													<Cloud
														className="size-4 shrink-0 {terminalServerId === server.id
															? 'text-emerald-500'
															: 'text-gray-400'}"
														strokeWidth="2.5"
													/>
													<span class="truncate">{server.name || server.id}</span>
												</div>
												{#if terminalServerId === server.id}
													<svg
														xmlns="http://www.w3.org/2000/svg"
														viewBox="0 0 20 20"
														fill="currentColor"
														class="size-4 text-emerald-600 dark:text-emerald-400 shrink-0"
													>
														<path
															fill-rule="evenodd"
															d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
															clip-rule="evenodd"
														/>
													</svg>
												{/if}
											</button>
										{/each}
										{#if terminalServerId}
											<div
												class="border-t border-gray-100 dark:border-gray-800 mt-1.5 pt-1.5 px-0.5"
											>
												<div class="px-2.5 py-1 text-xs text-gray-500">
													{$i18n.t('Working Directory')}
												</div>
												<div class="px-2 pb-1">
													<input
														type="text"
														bind:value={terminalCwd}
														placeholder="/home/user/project"
														class="w-full bg-gray-50 dark:bg-gray-900 rounded-lg outline-hidden text-xs py-2 px-2.5 border-none placeholder:text-gray-400 dark:placeholder:text-gray-600"
														on:click={(e) => e.stopPropagation()}
														on:input={markDirty}
													/>
												</div>
											</div>
										{/if}
									</div>
								</Dropdown>
							</div>
						{/if}
					</div>
				</div>

				<!-- Status section -->
				<div>
					<div class="text-gray-500 text-xs mb-3">{$i18n.t('Status')}</div>
					<div class="space-y-2.5">
						<div class="flex items-center justify-between text-xs">
							<span class="text-gray-600 dark:text-gray-400">{$i18n.t('State')}</span>
							<div
								class="flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-xs transition {is_active
									? 'text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/10'
									: 'text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-800'}"
							>
								<span
									class="inline-block size-1.5 rounded-full {is_active
										? 'bg-emerald-500'
										: 'bg-gray-400'}"
								></span>
								<span>{is_active ? $i18n.t('Active') : $i18n.t('Paused')}</span>
							</div>
						</div>

						<div class="flex items-center justify-between text-xs">
							<span class="text-gray-600 dark:text-gray-400">{$i18n.t('Next run')}</span>
							<span class=" text-gray-700 dark:text-gray-300"
								>{formatNextRun(automation.next_runs?.[0] ?? automation.next_run_at)}</span
							>
						</div>
						<div class="flex items-center justify-between text-xs">
							<span class="text-gray-600 dark:text-gray-400">{$i18n.t('Last ran')}</span>
							<span class=" text-gray-700 dark:text-gray-300"
								>{automation.last_run_at
									? formatNextRun(automation.last_run_at)
									: $i18n.t('Never')}</span
							>
						</div>
					</div>
				</div>

				<div class="flex-1 flex flex-col min-h-0">
					<div class="text-gray-500 text-xs mb-2 shrink-0">
						{$i18n.t('Execution Logs')}
					</div>
					<div class="flex-1 overflow-y-auto scrollbar-hidden w-full">
						{#if runsLoading}
							<div class="flex justify-center py-4">
								<Spinner className="size-4" />
							</div>
						{:else if runs.length === 0}
							<div class="text-xs text-gray-400 py-4 tabular-nums">
								{$i18n.t('No execution logs available yet')}
							</div>
						{:else}
							<div class="space-y-0.5 w-full">
								{#each runs as run (run.id)}
									<button
										class="w-full text-left flex items-center gap-2.5 px-3 py-2 rounded-xl hover:bg-gray-100/80 dark:hover:bg-gray-850/80 transition-colors {run.chat_id
											? 'cursor-pointer'
											: 'cursor-default'}"
										on:click={() => {
											if (run.chat_id) goto(`/c/${run.chat_id}`);
										}}
										type="button"
									>
										<div class="shrink-0 flex items-center justify-center">
											{#if run.status === 'success'}
												<svg
													xmlns="http://www.w3.org/2000/svg"
													viewBox="0 0 20 20"
													fill="currentColor"
													class="size-3 text-emerald-500"
													><path
														fill-rule="evenodd"
														d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z"
														clip-rule="evenodd"
													/></svg
												>
											{:else if run.status === 'error'}
												<svg
													xmlns="http://www.w3.org/2000/svg"
													viewBox="0 0 20 20"
													fill="currentColor"
													class="size-3 text-red-500"
													><path
														fill-rule="evenodd"
														d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z"
														clip-rule="evenodd"
													/></svg
												>
											{:else}
												<svg
													xmlns="http://www.w3.org/2000/svg"
													viewBox="0 0 20 20"
													fill="currentColor"
													class="size-3 text-blue-500"
													><path
														d="M10 18a8 8 0 100-16 8 8 0 000 16zm.75-13a.75.75 0 00-1.5 0v5c0 .414.336.75.75.75h4a.75.75 0 000-1.5h-3.25V5z"
													/></svg
												>
											{/if}
										</div>
										<div class="flex-1 min-w-0">
											<div class="text-xs text-gray-800 dark:text-gray-200 truncate">
												{automation.name}
											</div>
										</div>
										<span class="shrink-0 text-[10px] text-gray-500 font-mono"
											>{formatRunTime(run.created_at)}</span
										>
									</button>
								{/each}
							</div>
						{/if}
					</div>
				</div>
			</div>
		</div>
	</div>
</div>
