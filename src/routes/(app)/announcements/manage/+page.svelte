<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { toast } from 'svelte-sonner';

	import {
		listAnnouncements,
		createAnnouncement,
		updateAnnouncement,
		deleteAnnouncement,
		destroyAnnouncement,
		type Announcement
	} from '$lib/apis/announcements';
	import { user } from '$lib/stores';

	const i18n = getContext('i18n');

	let loading = true;
let saving = false;
let announcements: Announcement[] = [];
let editing: Announcement | null = null;
let pendingAction: { type: 'archive' | 'delete'; item: Announcement } | null = null;
let form = {
	title: '',
	content: '',
	status: 'active'
};

	const resetForm = () => {
		editing = null;
		form = {
			title: '',
			content: '',
			status: 'active'
		};
	};

	const load = async () => {
		loading = true;
		const res = await listAnnouncements(localStorage.token).catch((error) => {
			console.error(error);
			const msg =
				typeof error === 'string'
					? error
					: error?.detail ?? error?.message ?? $i18n.t('Failed to load announcements');
			toast.error(msg);
			return null;
		});
		if (res) {
			announcements = res;
		}
		loading = false;
	};

	const submit = async () => {
		if (!form.title || !form.content) {
			toast.error($i18n.t('Please fill title and content'));
			return;
		}
		saving = true;
		if (editing) {
			await updateAnnouncement(localStorage.token, editing.id, form).catch((error) => {
				console.error(error);
				toast.error(error?.detail ?? error?.message ?? $i18n.t('Update failed'));
			});
		} else {
			await createAnnouncement(localStorage.token, form).catch((error) => {
				console.error(error);
				toast.error(error?.detail ?? error?.message ?? $i18n.t('Create failed'));
			});
		}
		saving = false;
		await load();
		resetForm();
	};

	const archive = (item: Announcement) => {
		pendingAction = { type: 'archive', item };
	};

	const remove = (item: Announcement) => {
		pendingAction = { type: 'delete', item };
	};

	const confirmAction = async () => {
		if (!pendingAction) return;
		const { type, item } = pendingAction;
		pendingAction = null;

		if (type === 'archive') {
			await deleteAnnouncement(localStorage.token, item.id).catch((error) => {
				console.error(error);
				toast.error(error?.detail ?? error?.message ?? $i18n.t('Failed to archive'));
			});
		} else {
			await destroyAnnouncement(localStorage.token, item.id).catch((error) => {
				console.error(error);
				toast.error(error?.detail ?? error?.message ?? $i18n.t('删除失败'));
			});
		}
		await load();
	};

	const cancelAction = () => {
		pendingAction = null;
	};

	onMount(async () => {
		const currentUser = get(user);
		if (!currentUser || currentUser.role !== 'admin') {
			goto('/');
			return;
		}
		await load();
	});
</script>

<div class="mx-auto flex max-w-5xl flex-col gap-6 px-6 py-8">
	<div class="flex items-center justify-between">
		<div>
			<div class="text-2xl font-semibold text-gray-900 dark:text-gray-50">
				{$i18n.t('公告管理')}
			</div>
			<p class="text-sm text-gray-500 dark:text-gray-400">
				{$i18n.t('创建、更新或归档平台公告，发布后用户登录会看到最新公告。')}
			</p>
		</div>
	</div>

	<div class="grid gap-4 rounded-2xl border border-gray-100 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900">
		<div class="grid gap-3 md:grid-cols-2">
			<label class="flex flex-col gap-2 text-sm">
				<span class="text-gray-600 dark:text-gray-300">{$i18n.t('标题')}</span>
				<input
					class="w-full rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-gray-800 dark:bg-gray-950"
					placeholder={$i18n.t('请输入公告标题')}
					bind:value={form.title}
				/>
			</label>
			<label class="flex flex-col gap-2 text-sm">
				<span class="text-gray-600 dark:text-gray-300">{$i18n.t('状态')}</span>
				<select
					class="w-full rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-gray-800 dark:bg-gray-950"
					bind:value={form.status}
				>
					<option value="active">{$i18n.t('Active')}</option>
					<option value="archived">{$i18n.t('Archived')}</option>
				</select>
			</label>
		</div>
		<label class="flex flex-col gap-2 text-sm">
			<span class="text-gray-600 dark:text-gray-300">{$i18n.t('正文')}</span>
			<textarea
				class="min-h-[140px] rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-gray-800 dark:bg-gray-950"
				placeholder={$i18n.t('支持纯文本或 Markdown')}
				bind:value={form.content}
			></textarea>
		</label>
		<div class="flex gap-3">
			<button
				class="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:opacity-60"
				on:click={submit}
				disabled={saving}
			>
				{editing ? $i18n.t('保存') : $i18n.t('发布')}
			</button>
			{#if editing}
				<button
					class="rounded-xl border border-gray-200 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-50 dark:border-gray-800 dark:text-gray-200 dark:hover:bg-gray-800"
					on:click={resetForm}
				>
					{$i18n.t('取消编辑')}
				</button>
			{/if}
		</div>
	</div>

	<div class="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900">
		<div class="flex items-center justify-between">
			<div class="text-lg font-semibold text-gray-900 dark:text-gray-50">
				{$i18n.t('公告列表')}
			</div>
			{#if loading}
				<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Loading...')}</div>
			{/if}
		</div>

		<div class="mt-4 divide-y divide-gray-100 dark:divide-gray-800">
			{#if announcements.length === 0}
				<div class="py-6 text-sm text-gray-500 dark:text-gray-400">
					{$i18n.t('暂无公告')}
				</div>
			{:else}
				{#each announcements as item}
					<div class="flex flex-col gap-2 py-4 md:flex-row md:items-center md:justify-between">
						<div class="flex flex-1 flex-col gap-1">
							<div class="flex items-center gap-2">
								<div class="text-base font-semibold text-gray-900 dark:text-gray-50">{item.title}</div>
								{#if item.status !== 'active'}
									<span class="rounded-full bg-gray-200 px-2 py-0.5 text-[10px] font-semibold text-gray-600 dark:bg-gray-800 dark:text-gray-300">
										{item.status}
									</span>
								{/if}
							</div>
							<p class="text-sm text-gray-600 line-clamp-2 dark:text-gray-300">{item.content}</p>
							<div class="text-xs text-gray-500 dark:text-gray-400">
								{$i18n.t('更新于')}: {new Date(item.updated_at / 1_000_000).toLocaleString()}
							</div>
						</div>
						<div class="flex gap-2">
							<button
								class="rounded-xl border border-gray-200 px-3 py-1.5 text-sm font-semibold text-gray-700 transition hover:bg-gray-50 dark:border-gray-800 dark:text-gray-200 dark:hover:bg-gray-800"
								on:click={() => {
									editing = item;
									form = {
										title: item.title,
										content: item.content,
										status: item.status ?? 'active'
									};
								}}
							>
								{$i18n.t('编辑')}
							</button>
							<button
								class="rounded-xl border border-red-200 px-3 py-1.5 text-sm font-semibold text-red-600 transition hover:bg-red-50 dark:border-red-900/50 dark:text-red-200 dark:hover:bg-red-950/30"
								on:click={() => archive(item)}
							>
								{$i18n.t('归档')}
							</button>
							<button
								class="rounded-xl border border-red-300 px-3 py-1.5 text-sm font-semibold text-red-700 transition hover:bg-red-100 dark:border-red-900/70 dark:text-red-100 dark:hover:bg-red-950/40"
								type="button"
								on:click={() => remove(item)}
							>
								{$i18n.t('删除')}
							</button>
						</div>
					</div>
				{/each}
			{/if}
		</div>
	</div>

	{#if pendingAction}
		<div class="fixed inset-0 z-40 flex items-center justify-center bg-black/40 px-4">
			<div class="w-full max-w-md rounded-2xl border border-gray-200 bg-white p-6 shadow-xl dark:border-gray-800 dark:bg-gray-900">
				<div class="text-lg font-semibold text-gray-900 dark:text-gray-50">
					{pendingAction.type === 'archive' ? $i18n.t('确认归档') : $i18n.t('确认删除')}
				</div>
				<p class="mt-2 text-sm text-gray-600 dark:text-gray-300">
					{pendingAction.type === 'archive'
						? $i18n.t('归档后将从用户端隐藏，确认归档这条公告吗？')
						: $i18n.t('删除后不可恢复，确认删除这条公告吗？')}
				</p>
				<div class="mt-4 space-y-1 text-sm">
					<div class="font-semibold text-gray-900 dark:text-gray-100">{pendingAction.item.title}</div>
					<div class="line-clamp-2 text-gray-600 dark:text-gray-300">
						{pendingAction.item.content}
					</div>
				</div>
				<div class="mt-6 flex justify-end gap-3">
					<button
						class="rounded-xl border border-gray-200 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-50 dark:border-gray-800 dark:text-gray-200 dark:hover:bg-gray-800"
						type="button"
						on:click={cancelAction}
					>
						{$i18n.t('取消')}
					</button>
					<button
						class="rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-red-700"
						type="button"
						on:click={confirmAction}
					>
						{pendingAction.type === 'archive' ? $i18n.t('归档') : $i18n.t('删除')}
					</button>
				</div>
			</div>
		</div>
	{/if}
</div>
