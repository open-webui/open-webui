<script lang="ts">
	import { getContext, onDestroy } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	const i18n = getContext<Writable<i18nType>>('i18n');

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	dayjs.extend(relativeTime);
	dayjs.extend(localizedFormat);

	import { getUsers } from '$lib/apis/users';
	import { toast } from 'svelte-sonner';

	import { addUserToGroup, removeUserFromGroup } from '$lib/apis/groups';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import Pagination from '$lib/components/common/Pagination.svelte';
	import ArrowDownTray from '$lib/components/icons/ArrowDownTray.svelte';
	import ArrowUpTray from '$lib/components/icons/ArrowUpTray.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	type GroupUser = {
		id: string;
		name: string;
		email: string;
		role: string;
		last_active_at: number;
		group_ids?: string[];
	};

	type CsvImportRow = {
		idx: number;
		email: string;
	};

	type CsvParseResult = {
		validRows: CsvImportRow[];
		invalidRows: number[];
	};

	type GroupMemberUpdate = {
		member_count?: number;
	};

	const BATCH_SIZE = 10;

	const isPresent = <T,>(value: T | null | undefined): value is T => value != null;

	const chunk = <T,>(items: T[], size: number) =>
		Array.from({ length: Math.ceil(items.length / size) }, (_, idx) =>
			items.slice(idx * size, idx * size + size)
		);

	const unique = <T,>(items: T[]) => [...new Set(items)];

	const parseCsvRows = (csv: string): CsvParseResult =>
		csv
			.split(/\r?\n/)
			.slice(1)
			.map((row, index) => ({ row, idx: index + 1 }))
			.reduce<CsvParseResult>(
				(acc, { row, idx }) => {
					const columns = row.split(',').map((col) => col.trim());
					const isBlank = columns.length === 1 && columns[0] === '';
					const email = columns[1]?.toLowerCase();

					if (isBlank) return acc;
					if (columns.length !== 2 || !email) {
						return { ...acc, invalidRows: [...acc.invalidRows, idx] };
					}

					return { ...acc, validRows: [...acc.validRows, { idx, email }] };
				},
				{ validRows: [], invalidRows: [] }
			);

	export let groupId: string;
	export let userCount = 0;
	export let onMemberChange: Function = () => {};

	let users: GroupUser[] | null = null;
	let total: number | null = null;

	let query = '';
	let searchDebounceTimer: ReturnType<typeof setTimeout>;
	let inputFiles: FileList | null = null;
	let fileInputElement: HTMLInputElement;
	let importing = false;
	let showImportMenu = false;
	let orderBy = groupId ? `group_id:${groupId}` : 'last_active_at'; // default sort key
	let direction = 'desc'; // default sort order

	let page = 1;

	const setSortKey = (key: string) => {
		if (orderBy === key) {
			direction = direction === 'asc' ? 'desc' : 'asc';
		} else {
			orderBy = key;
			direction = 'asc';
		}
		page = 1;
	};

	const roleClass = (role: string) => {
		if (role === 'admin') {
			return 'text-[#4f6f93] dark:text-[#8ba6c6]';
		}
		if (role === 'user') {
			return 'text-[#4f7a5a] dark:text-[#8db395]';
		}
		return 'text-gray-500 dark:text-gray-400';
	};

	const getUserList = async () => {
		try {
			const res = await getUsers(localStorage.token, query, orderBy, direction, page).catch(
				(error) => {
					toast.error(`${error}`);
					return null;
				}
			);

			if (res) {
				users = res.users;
				total = res.total;
			}
		} catch (err) {
			console.error(err);
		}
	};

	const toggleMember = async (userId: string, state: string) => {
		let res = null;

		if (state === 'checked') {
			res = await addUserToGroup(localStorage.token, groupId, [userId]).catch((error) => {
				toast.error(`${error}`);
				return null;
			});
		} else {
			res = await removeUserFromGroup(localStorage.token, groupId, [userId]).catch((error) => {
				toast.error(`${error}`);
				return null;
			});
		}

		if (res) {
			userCount = res.member_count ?? userCount;
			onMemberChange(res);
		}

		await getUserList();
	};

	const clearFileInput = () => {
		inputFiles = null;
		if (fileInputElement) {
			fileInputElement.value = '';
		}
	};

	const getExactUserIdByEmail = async ({ idx, email }: CsvImportRow) =>
		getUsers(localStorage.token, email)
			.then((res) => {
				const user = ((res?.users ?? []) as { id?: string; email?: string }[]).find(
					(u) => u.email?.toLowerCase() === email
				);

				if (user?.id) return user.id;

				toast.error(`Row ${idx + 1}: ${$i18n.t('User not found.')}`);
				return null;
			})
			.catch((error) => {
				toast.error(`Row ${idx + 1}: ${error}`);
				return null;
			});

	const resolveUserIds = async (rows: CsvImportRow[]) => {
		const resolvedUserIds: (string | null)[] = [];

		for (const rowsBatch of chunk(rows, BATCH_SIZE)) {
			resolvedUserIds.push(...(await Promise.all(rowsBatch.map(getExactUserIdByEmail))));
		}

		return unique(resolvedUserIds.filter(isPresent));
	};

	const addUserIdToCurrentGroup = async (userId: string) =>
		addUserToGroup(localStorage.token, groupId, [userId]).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

	const addUserIdsToCurrentGroup = (userIds: string[]) =>
		userIds.reduce<Promise<GroupMemberUpdate | null>>(async (lastGroupPromise, userId) => {
			const lastGroup = await lastGroupPromise;
			const group = await addUserIdToCurrentGroup(userId);

			if (!group) return lastGroup;

			userCount = group.member_count ?? userCount;
			return group;
		}, Promise.resolve(null));

	const importCsv = async (file: File) => {
		if (!groupId || importing) return;

		importing = true;

		try {
			const { validRows, invalidRows } = parseCsvRows(await file.text());
			const initialCount = userCount;
			invalidRows.forEach((idx) => toast.error(`Row ${idx + 1}: ${$i18n.t('Invalid format.')}`));

			const lastGroup = await addUserIdsToCurrentGroup(await resolveUserIds(validRows));

			if (lastGroup) {
				onMemberChange(lastGroup);
			}

			const importedCount = Math.max(0, userCount - initialCount);
			if (importedCount > 0) {
				toast.success(
					$i18n.t('Successfully imported {{userCount}} users.', { userCount: importedCount })
				);
			}

			await getUserList();
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			clearFileInput();
			importing = false;
		}
	};

	const handleFileChange = async () => {
		const file = inputFiles?.[0];
		if (!file) return;

		await importCsv(file);
	};

	const downloadCsvTemplate = () => {
		const url = URL.createObjectURL(new Blob(['Name,Email\n'], { type: 'text/csv;charset=utf-8' }));
		const a = document.createElement('a');
		a.href = url;
		a.download = 'group-import.csv';
		a.click();
		URL.revokeObjectURL(url);
	};

	$: if (page !== null && orderBy !== null && direction !== null) {
		getUserList();
	}

	const handleSearchInput = () => {
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(() => {
			if (page !== 1) {
				page = 1;
			} else {
				getUserList();
			}
		}, 300);
	};

	onDestroy(() => {
		clearTimeout(searchDebounceTimer);
	});
</script>

<div class=" max-h-full h-full w-full flex flex-col overflow-y-hidden">
	<div class="w-full h-fit mb-1.5">
		<input
			bind:this={fileInputElement}
			hidden
			bind:files={inputFiles}
			type="file"
			accept=".csv"
			disabled={importing}
			on:change={handleFileChange}
		/>

		<div class="flex flex-1 h-fit items-center gap-2">
			<div class="flex min-w-0 flex-1 items-center">
				<div class=" self-center mr-3">
					<Search />
				</div>
				<input
					class=" w-full text-sm pr-4 rounded-r-xl outline-hidden bg-transparent"
					bind:value={query}
					on:input={handleSearchInput}
					placeholder={$i18n.t('Search')}
				/>
			</div>

			<Dropdown bind:show={showImportMenu} align="end" sideOffset={6}>
				<button
					class="ml-1 flex shrink-0 items-center gap-0.5 rounded-lg px-1 py-0.5 text-xs font-normal text-gray-500 transition hover:text-gray-700 disabled:cursor-not-allowed disabled:opacity-60 dark:text-gray-400 dark:hover:text-gray-200"
					type="button"
					disabled={importing || !groupId}
					aria-label={$i18n.t('Import CSV')}
					title={$i18n.t('Import CSV')}
				>
					{#if importing}
						<Spinner className="size-3" />
						<span class="truncate">{$i18n.t('Importing...')}</span>
					{:else}
						<span class="truncate">{$i18n.t('Import')}</span>
						<ChevronDown className="size-2.5" strokeWidth="2.5" />
					{/if}
				</button>

				<div slot="content">
					<DropdownMenu className="min-w-[12rem]">
						<button
							on:click={() => {
								fileInputElement?.click();
								showImportMenu = false;
							}}
						>
							<ArrowUpTray className="size-3.5" />
							<span class="self-center truncate">{$i18n.t('Import CSV')}</span>
						</button>

						<button
							on:click={() => {
								downloadCsvTemplate();
								showImportMenu = false;
							}}
						>
							<ArrowDownTray className="size-3.5" />
							<span class="self-center truncate">{$i18n.t('Download CSV Template')}</span>
						</button>

						<div class="px-2 py-0.5 text-[0.625rem] leading-3 text-gray-400 dark:text-gray-500">
							{$i18n.t('CSV: Name,Email')}
						</div>
					</DropdownMenu>
				</div>
			</Dropdown>
		</div>
	</div>

	{#if users === null || total === null}
		<div class="my-10">
			<Spinner className="size-5" />
		</div>
	{:else}
		{#if users.length > 0}
			<div class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full">
				<table
					class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full"
				>
					<thead class="text-xs text-gray-800 uppercase bg-transparent dark:text-gray-200">
						<tr class=" border-b-[1.5px] border-gray-50/50 dark:border-gray-800/10">
							<th
								scope="col"
								class="px-2.5 py-1.5 cursor-pointer text-left w-8"
								on:click={() => setSortKey(`group_id:${groupId}`)}
							>
								<div class="flex gap-1.5 items-center">
									{$i18n.t('MBR')}

									{#if orderBy === `group_id:${groupId}`}
										<span class="font-normal"
											>{#if direction === 'asc'}
												<ChevronUp className="size-2" />
											{:else}
												<ChevronDown className="size-2" />
											{/if}
										</span>
									{:else}
										<span class="invisible">
											<ChevronUp className="size-2" />
										</span>
									{/if}
								</div>
							</th>

							<th
								scope="col"
								class="px-2.5 py-1.5 cursor-pointer select-none"
								on:click={() => setSortKey('name')}
							>
								<div class="flex gap-1.5 items-center">
									{$i18n.t('Name')}

									{#if orderBy === 'name'}
										<span class="font-normal"
											>{#if direction === 'asc'}
												<ChevronUp className="size-2" />
											{:else}
												<ChevronDown className="size-2" />
											{/if}
										</span>
									{:else}
										<span class="invisible">
											<ChevronUp className="size-2" />
										</span>
									{/if}
								</div>
							</th>
							<th
								scope="col"
								class="px-2.5 py-1.5 cursor-pointer select-none"
								on:click={() => setSortKey('role')}
							>
								<div class="flex gap-1.5 items-center">
									{$i18n.t('Role')}

									{#if orderBy === 'role'}
										<span class="font-normal"
											>{#if direction === 'asc'}
												<ChevronUp className="size-2" />
											{:else}
												<ChevronDown className="size-2" />
											{/if}
										</span>
									{:else}
										<span class="invisible">
											<ChevronUp className="size-2" />
										</span>
									{/if}
								</div>
							</th>

							<th
								scope="col"
								class="px-2.5 py-1.5 cursor-pointer select-none"
								on:click={() => setSortKey('last_active_at')}
							>
								<div class="flex gap-1.5 items-center">
									{$i18n.t('Last Active')}

									{#if orderBy === 'last_active_at'}
										<span class="font-normal"
											>{#if direction === 'asc'}
												<ChevronUp className="size-2" />
											{:else}
												<ChevronDown className="size-2" />
											{/if}
										</span>
									{:else}
										<span class="invisible">
											<ChevronUp className="size-2" />
										</span>
									{/if}
								</div>
							</th>
						</tr>
					</thead>
					<tbody class="">
						{#each users as user, userIdx (user?.id ?? userIdx)}
							<tr class="dark:border-gray-850 text-xs">
								<td class=" px-3 py-1 w-8">
									<div class="flex w-full justify-center">
										<Checkbox
											ariaLabel={user.name}
											state={(user?.group_ids ?? []).includes(groupId) ? 'checked' : 'unchecked'}
											on:change={(e) => {
												toggleMember(user.id, e.detail);
											}}
										/>
									</div>
								</td>
								<td class="px-3 py-1 font-normal text-gray-900 dark:text-white max-w-48">
									<Tooltip content={user.email} placement="top-start">
										<div class="flex items-center gap-2">
											<img
												class="rounded-full w-6 h-6 object-cover flex-shrink-0"
												src={`${WEBUI_API_BASE_URL}/users/${user.id}/profile/image`}
												alt="user"
											/>

											<div class="font-normal truncate">{user.name}</div>
										</div>
									</Tooltip>
								</td>
								<td class="px-3 py-1 min-w-[5rem] w-20">
									<span class="text-xs font-normal leading-4 capitalize {roleClass(user.role)}">
										{$i18n.t(user.role)}
									</span>
								</td>

								<td class=" px-3 py-1">
									{dayjs(user.last_active_at * 1000).fromNow()}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{:else}
			<div class="text-gray-500 text-xs text-center py-2 px-10">
				{$i18n.t('No users were found.')}
			</div>
		{/if}

		{#if total > 30}
			<Pagination bind:page count={total} perPage={30} />
		{/if}
	{/if}
</div>
