<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { models } from '$lib/stores';
	import Modal from '$lib/components/common/Modal.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import Cloud from '$lib/components/icons/Cloud.svelte';

	import { WEBUI_API_BASE_URL } from '$lib/constants';

	import {
		createAutomation,
		updateAutomationById,
		type AutomationForm,
		type AutomationResponse
	} from '$lib/apis/automations';
	import { getTerminalServers, type TerminalServer } from '$lib/apis/terminal/index';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let automation: AutomationResponse | null = null;

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

	let loading = false;
	let showScheduleDropdown = false;
	let showModelDropdown = false;
	let showTerminalDropdown = false;
	let modelSearch = '';
	let customRrule = '';

	// Terminal state
	let terminalServers: TerminalServer[] = [];
	let terminalServerId = '';
	let terminalCwd = '';

	$: terminalLabel = terminalServerId
		? terminalServers.find((s) => s.id === terminalServerId)?.name || 'Terminal'
		: $i18n.t('Terminal');

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

	const buildVisualRrule = (): string => {
		if (lastVisualFrequency === 'ONCE') {
			const dt = onceDate.replace(/-/g, '') + 'T' + onceTime.replace(/:/g, '') + '00';
			return `DTSTART:${dt}\nRRULE:FREQ=DAILY;COUNT=1`;
		}
		let parts = [`FREQ=${lastVisualFrequency}`];
		if (interval > 1) parts.push(`INTERVAL=${interval}`);
		if (lastVisualFrequency === 'WEEKLY' && selectedDays.length) {
			parts.push(`BYDAY=${selectedDays.join(',')}`);
		}
		if (lastVisualFrequency === 'MONTHLY') {
			parts.push(`BYMONTHDAY=${monthDay}`);
		}
		if (['DAILY', 'WEEKLY', 'MONTHLY'].includes(lastVisualFrequency)) {
			parts.push(`BYHOUR=${hour}`);
		}
		parts.push(`BYMINUTE=${minute}`);
		return `RRULE:${parts.join(';')}`;
	};

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

	const buildRrule = (): string => {
		if (frequency === 'CUSTOM') return customRrule;
		if (frequency === 'ONCE') {
			const dt = onceDate.replace(/-/g, '') + 'T' + onceTime.replace(/:/g, '') + '00';
			return `DTSTART:${dt}\nRRULE:FREQ=DAILY;COUNT=1`;
		}
		let parts = [`FREQ=${frequency}`];
		if (interval > 1) parts.push(`INTERVAL=${interval}`);
		if (frequency === 'WEEKLY' && selectedDays.length) {
			parts.push(`BYDAY=${selectedDays.join(',')}`);
		}
		if (frequency === 'MONTHLY') {
			parts.push(`BYMONTHDAY=${monthDay}`);
		}
		if (['DAILY', 'WEEKLY', 'MONTHLY'].includes(frequency)) {
			parts.push(`BYHOUR=${hour}`);
		}
		parts.push(`BYMINUTE=${minute}`);
		return `RRULE:${parts.join(';')}`;
	};

	const parseRrule = (s: string) => {
		// Detect ONCE (COUNT=1 with DTSTART)
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

	const scheduleLabel = (freq, intv, h, min, days, mDay) => {
		if (freq === 'ONCE') return 'Once';
		if (freq === 'HOURLY') return 'Hourly';
		if (freq === 'DAILY') return 'Daily';
		if (freq === 'WEEKLY') return 'Weekly';
		if (freq === 'MONTHLY') return 'Monthly';
		if (freq === 'CUSTOM') return 'Custom';
		return 'Schedule';
	};

	const submitHandler = async () => {
		if (!name.trim() || !prompt.trim() || !model_id.trim()) {
			toast.error($i18n.t('Name, prompt, and model are required'));
			return;
		}
		if (frequency === 'ONCE') {
			const scheduled = new Date(`${onceDate}T${onceTime}`);
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
		// Load terminal servers
		try {
			terminalServers = await getTerminalServers(localStorage.token);
		} catch {
			terminalServers = [];
		}

		if (automation) {
			name = automation.name;
			prompt = automation.data.prompt;
			model_id = automation.data.model_id;
			is_active = automation.is_active;
			parseRrule(automation.data.rrule);
			terminalServerId = automation.data.terminal?.server_id || '';
			terminalCwd = automation.data.terminal?.cwd || '';
		} else {
			name = '';
			prompt = '';
			model_id = '';
			is_active = true;
			frequency = 'DAILY';
			interval = 1;
			onceDate = '';
			onceTime = '09:00';
			hour = 9;
			minute = 0;
			selectedDays = [];
			monthDay = 1;
			terminalServerId = '';
			terminalCwd = '';
		}
		showScheduleDropdown = false;
		showTerminalDropdown = false;
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
				<!-- Schedule dropdown -->
				<Dropdown bind:show={showScheduleDropdown} side="top" align="start">
					<button
						type="button"
						class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-2xl text-xs transition
							text-gray-600 dark:text-gray-400 hover:bg-black/5 dark:hover:bg-white/5"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-3.5"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
							/>
						</svg>
						<span class="whitespace-nowrap"
							>{scheduleLabel(frequency, interval, hour, minute, selectedDays, monthDay)}</span
						>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="2"
							stroke="currentColor"
							class="size-2.5"
						>
							<path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
						</svg>
					</button>

					<div
						slot="content"
						class="rounded-2xl shadow-lg border border-gray-200 dark:border-gray-800 flex flex-col bg-white dark:bg-gray-850 w-48 p-1"
					>
						<div class="px-2 text-xs text-gray-500 py-1">
							{$i18n.t('Schedule')}
						</div>

						<div class="px-1.5 mt-0.5 mb-2">
							<select
								class="w-full bg-transparent rounded-xl text-xs py-1.5 px-1.5 outline-hidden"
								bind:value={frequency}
								on:click={(e) => e.stopPropagation()}
							>
								{#each FREQUENCIES as f}
									<option value={f.key}>{f.label}</option>
								{/each}
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
								/>
							</div>
						{:else if frequency !== 'HOURLY'}
							<div class="flex gap-2 flex-wrap items-center px-3 pb-2 text-xs">
								{#if frequency === 'ONCE'}
									<div class="flex items-center gap-1.5">
										<input
											type="date"
											bind:value={onceDate}
											min={new Date().toISOString().split('T')[0]}
											class="bg-transparent outline-hidden text-xs dark:color-scheme-dark"
											on:click={(e) => e.stopPropagation()}
										/>
									</div>
									<div class="flex items-center gap-1.5">
										<input
											type="time"
											bind:value={onceTime}
											class="bg-transparent outline-hidden text-xs dark:color-scheme-dark"
											on:click={(e) => e.stopPropagation()}
										/>
									</div>
								{:else}
									<div class="flex items-center gap-1.5">
										<span class="text-xs text-gray-500 mr-0.5">{$i18n.t('Time')}</span>
										<input
											type="time"
											value={`${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`}
											on:input={(e) => {
												const [h, m] = e.currentTarget.value.split(':').map(Number);
												hour = h;
												minute = m;
											}}
											class="bg-transparent text-center outline-hidden text-xs dark:color-scheme-dark"
											on:click={(e) => e.stopPropagation()}
										/>
									</div>
								{/if}

								{#if frequency === 'MONTHLY'}
									<div class="flex items-center gap-1.5">
										<span class="text-xs text-gray-500">{$i18n.t('Day')}</span>
										<input
											type="number"
											bind:value={monthDay}
											min={1}
											max={31}
											class="w-8 bg-transparent text-center outline-hidden text-xs"
											on:click={(e) => e.stopPropagation()}
										/>
									</div>
								{/if}
							</div>

							{#if frequency === 'WEEKLY'}
								<div class="flex gap-1 px-2 pb-2">
									{#each DAYS as d}
										<button
											type="button"
											class="flex-1 py-1 text-xs rounded-xl transition {selectedDays.includes(d.key)
												? 'bg-gray-50 dark:bg-gray-800 text-black dark:text-gray-100'
												: 'text-gray-400 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-200'}"
											on:click={() => {
												if (selectedDays.includes(d.key)) {
													selectedDays = selectedDays.filter((x) => x !== d.key);
												} else {
													selectedDays = [...selectedDays, d.key];
												}
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

				<!-- Model dropdown -->
				<Dropdown bind:show={showModelDropdown} side="top" align="start">
					<button
						type="button"
						class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-2xl text-xs transition
							text-gray-600 dark:text-gray-400 hover:bg-black/5 dark:hover:bg-white/5"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-3.5 shrink-0"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z"
							/>
						</svg>
						<span class="whitespace-nowrap max-w-32 truncate">{modelLabel}</span>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="2"
							stroke="currentColor"
							class="size-2.5"
						>
							<path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
						</svg>
					</button>

					<div
						slot="content"
						class="rounded-2xl shadow-lg border border-gray-200 dark:border-gray-800 flex flex-col bg-white dark:bg-gray-850 w-72 p-1"
					>
						<div class="flex items-center gap-2 px-2.5 py-1.5">
							<Search className="size-3.5" strokeWidth="2.5" />
							<input
								bind:value={modelSearch}
								class="w-full text-sm bg-transparent outline-hidden"
								placeholder={$i18n.t('Search a model')}
								autocomplete="off"
								on:click={(e) => e.stopPropagation()}
							/>
						</div>

						<div class="overflow-y-auto scrollbar-thin max-h-60">
							<div class="px-2 text-xs text-gray-500 py-1">
								{$i18n.t('Models')}
							</div>

							{#each filteredModels as model (model.id)}
								<button
									class="px-2.5 py-1.5 rounded-xl w-full text-left text-sm {model_id === model.id
										? 'bg-gray-50 dark:bg-gray-800'
										: ''}"
									type="button"
									on:click={() => {
										model_id = model.id;
										showModelDropdown = false;
										modelSearch = '';
									}}
								>
									<div class="flex text-black dark:text-gray-100 line-clamp-1">
										<img
											src={`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${encodeURIComponent(model.id)}`}
											alt={model?.name ?? model.id}
											class="rounded-full size-5 items-center mr-2"
											loading="lazy"
											on:error={(e) => {
												e.currentTarget.src = '/favicon.png';
											}}
										/>
										<div class="truncate">
											{model.name}
										</div>
									</div>
								</button>
							{:else}
								<div class="block px-3 py-2 text-sm text-gray-700 dark:text-gray-100">
									{$i18n.t('No results found')}
								</div>
							{/each}
						</div>
					</div>
				</Dropdown>

				<!-- Terminal dropdown -->
				{#if terminalServers.length > 0}
					<Dropdown bind:show={showTerminalDropdown} side="top" align="start">
						<button
							type="button"
							class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-2xl text-xs transition
								{terminalServerId
								? 'text-black dark:text-gray-100'
								: 'text-gray-600 dark:text-gray-400'}
								hover:bg-black/5 dark:hover:bg-white/5"
						>
							<Cloud className="size-3.5 shrink-0" strokeWidth="2" />
							<span class="whitespace-nowrap max-w-32 truncate">{terminalLabel}</span>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="2"
								stroke="currentColor"
								class="size-2.5"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
							</svg>
						</button>

						<div
							slot="content"
							class="rounded-2xl shadow-lg border border-gray-200 dark:border-gray-800 flex flex-col bg-white dark:bg-gray-850 min-w-56 max-w-56 p-1"
						>
							<div class="px-2 text-xs text-gray-500 py-1">
								{$i18n.t('Terminal')}
							</div>

							{#each terminalServers as server (server.id)}
								<button
									class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl {terminalServerId ===
									server.id
										? 'bg-gray-50 dark:bg-gray-800/50'
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
									}}
								>
									<div class="flex flex-1 gap-2 items-center truncate">
										<Cloud className="size-4 shrink-0" strokeWidth="2" />
										<span class="truncate">{server.name || server.id}</span>
									</div>
									{#if terminalServerId === server.id}
										<div class="shrink-0 text-emerald-600 dark:text-emerald-400">
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 20 20"
												fill="currentColor"
												class="size-4"
											>
												<path
													fill-rule="evenodd"
													d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
													clip-rule="evenodd"
												/>
											</svg>
										</div>
									{/if}
								</button>
							{/each}

							{#if terminalServerId}
								<div class="border-t border-gray-100 dark:border-gray-800 mt-1 pt-1">
									<div class="px-2.5 py-1 text-xs text-gray-500">
										{$i18n.t('Working Directory')}
									</div>
									<div class="px-2">
										<input
											type="text"
											bind:value={terminalCwd}
											placeholder="/home/user/project"
											class="w-full bg-transparent outline-hidden text-xs py-1.5 placeholder:text-gray-400 dark:placeholder:text-gray-600"
											on:click={(e) => e.stopPropagation()}
										/>
									</div>
								</div>
							{/if}
						</div>
					</Dropdown>
				{/if}
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
