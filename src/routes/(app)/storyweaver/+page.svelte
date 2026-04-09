<script lang="ts">
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import {
		novels,
		currentNovel,
		swLoading,
		swError,
		createNovel,
		updateNovel,
		deleteNovel,
		selectNovel,
		deselectNovel
	} from '$lib/stores/sw';
	import type { Novel, NovelStatus } from '$lib/apis/sw';

	const i18n = getContext('i18n');

	// ── État local du formulaire de création/édition
	let showCreateForm = false;
	let editingNovel: Novel | null = null;

	let formTitle = '';
	let formDescription = '';
	let formStatus: NovelStatus = 'draft';

	function openCreateForm() {
		editingNovel = null;
		formTitle = '';
		formDescription = '';
		formStatus = 'draft';
		showCreateForm = true;
	}

	function openEditForm(novel: Novel) {
		editingNovel = novel;
		formTitle = novel.title;
		formDescription = novel.description ?? '';
		formStatus = novel.status;
		showCreateForm = true;
	}

	function closeForm() {
		showCreateForm = false;
		editingNovel = null;
	}

	async function handleSubmit() {
		const token = localStorage.getItem('token');
		if (!token) return;

		if (editingNovel) {
			await updateNovel(token, editingNovel.id, {
				title: formTitle,
				description: formDescription || undefined,
				status: formStatus
			});
		} else {
			const created = await createNovel(token, {
				title: formTitle,
				description: formDescription || undefined,
				status: formStatus
			});
			if (created) closeForm();
			return;
		}
		closeForm();
	}

	async function handleSelect(id: string) {
		const token = localStorage.getItem('token');
		if (!token) return;
		await selectNovel(token, id);
	}

	async function handleDeselect() {
		const token = localStorage.getItem('token');
		if (!token) return;
		await deselectNovel(token);
	}

	async function handleDelete(novel: Novel) {
		if (!confirm(`Supprimer « ${novel.title} » ? Cette action est irréversible.`)) return;
		const token = localStorage.getItem('token');
		if (!token) return;
		await deleteNovel(token, novel.id);
	}

	function goToKB(novelId: string) {
		goto(`/storyweaver/${novelId}/kb`);
	}

	const STATUS_LABELS: Record<NovelStatus, string> = {
		draft: '✏️ Brouillon',
		'in-progress': '🚀 En cours',
		completed: '✅ Terminé',
		archived: '📦 Archivé'
	};

	const STATUS_CLASSES: Record<NovelStatus, string> = {
		draft: 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300',
		'in-progress': 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300',
		completed: 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300',
		archived: 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300'
	};
</script>

<div class="flex flex-col gap-6 py-6">

	<!-- En-tête -->
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-2xl font-bold dark:text-white">📚 Mes Romans</h1>
			<p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
				Sélectionnez un roman pour injecter son contexte dans le chat.
			</p>
		</div>
		<button
			id="sw-create-novel-btn"
			class="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium transition shadow-sm"
			on:click={openCreateForm}
		>
			<span class="text-base">+</span>
			<span>Nouveau roman</span>
		</button>
	</div>

	<!-- Erreur -->
	{#if $swError}
		<div class="p-3 rounded-xl bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm" role="alert">
			{$swError}
		</div>
	{/if}

	<!-- Roman courant -->
	{#if $currentNovel}
		<div class="p-4 rounded-2xl border-2 border-indigo-300 dark:border-indigo-700 bg-indigo-50 dark:bg-indigo-900/20 flex items-center justify-between gap-4">
			<div class="flex items-center gap-3">
				<div class="text-2xl">✍️</div>
				<div>
					<div class="text-xs font-medium text-indigo-500 dark:text-indigo-400 uppercase tracking-wide">Roman actif</div>
					<div class="font-semibold text-indigo-900 dark:text-indigo-100">{$currentNovel.title}</div>
					{#if $currentNovel.description}
						<div class="text-sm text-indigo-600 dark:text-indigo-300 mt-0.5">{$currentNovel.description}</div>
					{/if}
				</div>
			</div>
			<div class="flex items-center gap-2 shrink-0">
				<button
					class="px-3 py-1.5 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-750 transition"
					on:click={() => goToKB($currentNovel.id)}
				>
					📖 Base de Connaissances
				</button>
				<button
					class="px-3 py-1.5 rounded-lg text-sm text-gray-500 hover:text-red-500 dark:text-gray-400 dark:hover:text-red-400 transition"
					on:click={handleDeselect}
				>
					Désélectionner
				</button>
			</div>
		</div>
	{/if}

	<!-- Liste des romans -->
	{#if $swLoading}
		<div class="flex justify-center py-12">
			<div class="w-6 h-6 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin"></div>
		</div>
	{:else if $novels.length === 0}
		<div class="flex flex-col items-center justify-center py-16 gap-4 text-center">
			<div class="text-5xl">📖</div>
			<div>
				<p class="font-medium text-gray-700 dark:text-gray-200">Aucun roman pour l'instant</p>
				<p class="text-sm text-gray-400 mt-1">Créez votre premier roman pour commencer à écrire.</p>
			</div>
			<button
				class="mt-2 px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium transition"
				on:click={openCreateForm}
			>
				+ Créer mon premier roman
			</button>
		</div>
	{:else}
		<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
			{#each $novels as novel (novel.id)}
				<div
					class="group relative flex flex-col gap-3 p-4 rounded-2xl border transition
					{$currentNovel?.id === novel.id
						? 'border-indigo-300 dark:border-indigo-700 bg-indigo-50 dark:bg-indigo-900/10 shadow-sm'
						: 'border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:border-gray-300 dark:hover:border-gray-700 hover:shadow-sm'}"
				>
					<!-- Badge statut -->
					<div class="flex items-start justify-between gap-2">
						<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {STATUS_CLASSES[novel.status]}">
							{STATUS_LABELS[novel.status]}
						</span>

						<!-- Actions rapides (visibles au hover) -->
						<div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
							<button
								title="Modifier"
								class="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 hover:text-gray-700 dark:hover:text-white transition text-sm"
								on:click={() => openEditForm(novel)}
							>
								✏️
							</button>
							<button
								title="Supprimer"
								class="p-1 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 hover:text-red-500 transition text-sm"
								on:click={() => handleDelete(novel)}
							>
								🗑️
							</button>
						</div>
					</div>

					<!-- Titre + description -->
					<div class="flex-1">
						<h2 class="font-semibold text-gray-900 dark:text-white text-base leading-snug">{novel.title}</h2>
						{#if novel.description}
							<p class="text-sm text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">{novel.description}</p>
						{/if}
					</div>

					<!-- CTA -->
					<div class="flex items-center gap-2 pt-2 border-t border-gray-100 dark:border-gray-800">
						{#if $currentNovel?.id === novel.id}
							<button
								class="flex-1 py-1.5 rounded-lg text-sm text-indigo-600 dark:text-indigo-400 font-medium bg-indigo-100 dark:bg-indigo-900/30 hover:bg-indigo-200 dark:hover:bg-indigo-900/50 transition"
								on:click={() => goToKB(novel.id)}
							>
								📖 Éditer la KB
							</button>
							<button
								class="py-1.5 px-2 rounded-lg text-xs text-gray-400 hover:text-red-400 transition"
								on:click={handleDeselect}
							>
								❌
							</button>
						{:else}
							<button
								id="sw-select-{novel.id}"
								class="flex-1 py-1.5 rounded-lg text-sm text-gray-700 dark:text-gray-200 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 hover:text-indigo-700 dark:hover:text-indigo-300 transition border border-transparent hover:border-indigo-200 dark:hover:border-indigo-800"
								on:click={() => handleSelect(novel.id)}
							>
								Sélectionner →
							</button>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

<!-- Modal création/édition -->
{#if showCreateForm}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
		role="dialog"
		aria-modal="true"
		aria-label={editingNovel ? 'Modifier le roman' : 'Créer un roman'}
		on:click|self={closeForm}
		on:keydown={(e) => e.key === 'Escape' && closeForm()}
	>
		<div class="w-full max-w-md mx-4 bg-white dark:bg-gray-900 rounded-2xl shadow-2xl p-6 flex flex-col gap-5">
			<div class="flex items-center justify-between">
				<h2 class="text-lg font-bold dark:text-white">
					{editingNovel ? '✏️ Modifier le roman' : '📚 Nouveau roman'}
				</h2>
				<button
					class="text-gray-400 hover:text-gray-700 dark:hover:text-white transition text-xl"
					on:click={closeForm}
					aria-label="Fermer"
				>
					×
				</button>
			</div>

			<div class="flex flex-col gap-4">
				<!-- Titre -->
				<div class="flex flex-col gap-1.5">
					<label class="text-sm font-medium text-gray-700 dark:text-gray-300" for="sw-novel-title">
						Titre <span class="text-red-500">*</span>
					</label>
					<input
						id="sw-novel-title"
						type="text"
						class="w-full px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 transition"
						placeholder="Ex: Le Don d'Elosth"
						bind:value={formTitle}
						required
					/>
				</div>

				<!-- Description -->
				<div class="flex flex-col gap-1.5">
					<label class="text-sm font-medium text-gray-700 dark:text-gray-300" for="sw-novel-desc">
						Description
					</label>
					<textarea
						id="sw-novel-desc"
						class="w-full px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 transition resize-none"
						placeholder="Résumé ou pitch du roman…"
						rows="3"
						bind:value={formDescription}
					/>
				</div>

				<!-- Statut -->
				<div class="flex flex-col gap-1.5">
					<label class="text-sm font-medium text-gray-700 dark:text-gray-300" for="sw-novel-status">
						Statut
					</label>
					<select
						id="sw-novel-status"
						class="w-full px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 transition"
						bind:value={formStatus}
					>
						<option value="draft">✏️ Brouillon</option>
						<option value="in-progress">🚀 En cours</option>
						<option value="completed">✅ Terminé</option>
						<option value="archived">📦 Archivé</option>
					</select>
				</div>
			</div>

			<div class="flex justify-end gap-3 pt-2">
				<button
					class="px-4 py-2 rounded-xl text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
					on:click={closeForm}
				>
					Annuler
				</button>
				<button
					id="sw-novel-submit"
					class="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium transition disabled:opacity-50 disabled:cursor-not-allowed"
					disabled={!formTitle.trim() || $swLoading}
					on:click={handleSubmit}
				>
					{$swLoading ? '…' : (editingNovel ? 'Enregistrer' : 'Créer')}
				</button>
			</div>
		</div>
	</div>
{/if}
