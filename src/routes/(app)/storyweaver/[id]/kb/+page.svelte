<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import {
		currentNovel,
		activeKB,
		swLoading,
		swError,
		loadActiveKB,
		addKBItem,
		updateKBItem,
		deleteKBItem
	} from '$lib/stores/sw';
	import type { KBSection, KBItem } from '$lib/apis/sw';

	const i18n = getContext('i18n');
	const novelId = $page.params.id;

	// ── Onglets KB
	type Tab = { id: KBSection; label: string; icon: string; schema: Record<string, { label: string; type: 'text' | 'textarea' | 'list'; placeholder?: string }> };

	const TABS: Tab[] = [
		{
			id: 'universe_docs',
			label: 'Univers',
			icon: '🌍',
			schema: {
				name: { label: 'Nom', type: 'text', placeholder: 'Ex: Magie Horgonienne' },
				type: { label: 'Type', type: 'text', placeholder: 'Ex: Système de magie' },
				description: { label: 'Description', type: 'textarea', placeholder: 'Description détaillée...' },
				notes: { label: 'Notes', type: 'textarea', placeholder: 'Notes libres...' }
			}
		},
		{
			id: 'characters',
			label: 'Personnages',
			icon: '👤',
			schema: {
				name: { label: 'Nom', type: 'text', placeholder: 'Ex: Aela' },
				role: { label: 'Rôle', type: 'text', placeholder: 'Ex: Héroïne principale' },
				age: { label: 'Âge', type: 'text', placeholder: 'Ex: 24' },
				traits: { label: 'Traits (séparés par virgule)', type: 'text', placeholder: 'Ex: Courageuse, Impulsive' },
				description: { label: 'Description', type: 'textarea', placeholder: 'Apparence, personnalité...' },
				backstory: { label: 'Backstory', type: 'textarea', placeholder: 'Histoire personnelle...' },
				goals: { label: 'Objectifs', type: 'textarea', placeholder: 'Ce que le personnage veut accomplir...' },
				notes: { label: 'Notes', type: 'textarea', placeholder: 'Notes libres...' }
			}
		},
		{
			id: 'locations',
			label: 'Lieux',
			icon: '🗺️',
			schema: {
				name: { label: 'Nom', type: 'text', placeholder: 'Ex: Forêt d\'Elen' },
				type: { label: 'Type', type: 'text', placeholder: 'Ex: Forêt, Ville, Donjon...' },
				region: { label: 'Région', type: 'text', placeholder: 'Ex: Nord de Rodienne' },
				description: { label: 'Description', type: 'textarea', placeholder: 'Description du lieu...' },
				atmosphere: { label: 'Atmosphère', type: 'textarea', placeholder: 'Ambiance, sons, odeurs...' },
				notes: { label: 'Notes', type: 'textarea' }
			}
		},
		{
			id: 'objects',
			label: 'Objets',
			icon: '⚔️',
			schema: {
				name: { label: 'Nom', type: 'text', placeholder: 'Ex: Épée d\'Elosth' },
				type: { label: 'Type', type: 'text', placeholder: 'Ex: Arme, Artefact, Relique...' },
				description: { label: 'Description', type: 'textarea', placeholder: 'Apparence et nature...' },
				powers: { label: 'Pouvoirs / Propriétés', type: 'textarea', placeholder: 'Capacités magiques ou spéciales...' },
				owner: { label: 'Propriétaire', type: 'text', placeholder: 'Ex: Aela' },
				notes: { label: 'Notes', type: 'textarea' }
			}
		},
		{
			id: 'timeline',
			label: 'Chronologie',
			icon: '📅',
			schema: {
				date: { label: 'Date / Période', type: 'text', placeholder: 'Ex: An 432, Avant la guerre...' },
				event: { label: 'Événement', type: 'text', placeholder: 'Courte description de l\'événement' },
				participants: { label: 'Participants (séparés par virgule)', type: 'text', placeholder: 'Ex: Aela, Bran, Keira' },
				consequences: { label: 'Conséquences', type: 'textarea', placeholder: 'Impact sur l\'histoire...' },
				notes: { label: 'Notes', type: 'textarea' }
			}
		}
	];

	let activeTab: KBSection = 'characters';
	let showItemForm = false;
	let editingItem: KBItem | null = null;
	let formData: Record<string, string> = {};
	let searchQuery = '';

	$: activeTabDef = TABS.find((t) => t.id === activeTab)!;
	$: currentItems = ($activeKB?.[activeTab] ?? []) as KBItem[];
	$: filteredItems = searchQuery.trim()
		? currentItems.filter((item) =>
				Object.values(item).some((v) =>
					String(v).toLowerCase().includes(searchQuery.toLowerCase())
				)
		  )
		: currentItems;

	function openCreateForm() {
		editingItem = null;
		formData = Object.fromEntries(Object.keys(activeTabDef.schema).map((k) => [k, '']));
		showItemForm = true;
	}

	function openEditForm(item: KBItem) {
		editingItem = item;
		formData = Object.fromEntries(
			Object.keys(activeTabDef.schema).map((k) => [k, String(item[k] ?? '')])
		);
		showItemForm = true;
	}

	function closeItemForm() {
		showItemForm = false;
		editingItem = null;
	}

	async function handleItemSubmit() {
		const token = localStorage.getItem('token');
		if (!token) return;

		// Nettoyage : champs vides omis, traits → tableau si nécessaire
		const cleaned: Record<string, unknown> = {};
		for (const [k, v] of Object.entries(formData)) {
			if (v.trim()) {
				if (k === 'traits' || k === 'participants') {
					cleaned[k] = v.split(',').map((s) => s.trim()).filter(Boolean);
				} else {
					cleaned[k] = v.trim();
				}
			}
		}

		if (editingItem) {
			await updateKBItem(token, novelId, activeTab, editingItem.id, cleaned);
		} else {
			await addKBItem(token, novelId, activeTab, cleaned);
		}
		closeItemForm();
	}

	async function handleDeleteItem(item: KBItem) {
		const label = String(item['name'] ?? item['event'] ?? item.id);
		if (!confirm(`Supprimer « ${label} » ?`)) return;
		const token = localStorage.getItem('token');
		if (!token) return;
		await deleteKBItem(token, novelId, activeTab, item.id);
	}

	onMount(async () => {
		const token = localStorage.getItem('token');
		if (!token) { goto('/'); return; }

		// Charger la KB si pas déjà en mémoire ou si novel différent
		if (!$activeKB || $activeKB.novel_id !== novelId) {
			await loadActiveKB(token, novelId);
		}

		// Vérifier que le roman courant est bien celui de la route
		if ($currentNovel?.id !== novelId) {
			await import('$lib/stores/sw').then(({ loadNovels }) => loadNovels(token));
		}
	});

	function getItemTitle(item: KBItem): string {
		return String(item['name'] ?? item['event'] ?? item['title'] ?? '(sans titre)');
	}

	function getItemSubtitle(item: KBItem): string {
		return String(item['role'] ?? item['type'] ?? item['date'] ?? item['region'] ?? '');
	}
</script>

<div class="flex flex-col gap-6 py-6">

	<!-- En-tête -->
	<div class="flex items-center justify-between flex-wrap gap-3">
		<div>
			<button
				class="text-sm text-gray-400 hover:text-gray-700 dark:hover:text-white transition mb-1"
				on:click={() => goto('/storyweaver')}
			>
				← Retour aux romans
			</button>
			<h1 class="text-2xl font-bold dark:text-white">
				📖 Base de Connaissances
			</h1>
			{#if $currentNovel?.id === novelId}
				<p class="text-sm text-indigo-600 dark:text-indigo-400 mt-0.5 font-medium">
					✍️ {$currentNovel.title}
				</p>
			{/if}
		</div>

		<!-- Recherche -->
		<div class="relative">
			<span class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">🔍</span>
			<input
				type="text"
				class="pl-8 pr-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-400 transition w-56"
				placeholder="Rechercher…"
				bind:value={searchQuery}
			/>
		</div>
	</div>

	<!-- Erreur -->
	{#if $swError}
		<div class="p-3 rounded-xl bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm" role="alert">
			{$swError}
		</div>
	{/if}

	<!-- Onglets -->
	<div class="flex gap-1 flex-wrap border-b border-gray-200 dark:border-gray-800">
		{#each TABS as tab}
			<button
				id="sw-kb-tab-{tab.id}"
				class="flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium transition border-b-2 -mb-px rounded-t-lg
				{activeTab === tab.id
					? 'border-indigo-500 text-indigo-700 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-900/20'
					: 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-white hover:bg-gray-50 dark:hover:bg-gray-800'}"
				on:click={() => { activeTab = tab.id; searchQuery = ''; }}
			>
				<span>{tab.icon}</span>
				<span>{tab.label}</span>
				{#if ($activeKB?.[tab.id] ?? []).length > 0}
					<span class="px-1.5 py-0.5 rounded-full text-xs bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
						{($activeKB?.[tab.id] ?? []).length}
					</span>
				{/if}
			</button>
		{/each}
	</div>

	<!-- Contenu de l'onglet -->
	<div class="flex flex-col gap-4">
		<!-- Barre d'outils de section -->
		<div class="flex items-center justify-between">
			<span class="text-sm text-gray-500 dark:text-gray-400">
				{filteredItems.length} {filteredItems.length === 1 ? 'entrée' : 'entrées'}
				{searchQuery ? `pour « ${searchQuery} »` : ''}
			</span>
			<button
				id="sw-kb-add-{activeTab}"
				class="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium transition shadow-sm"
				on:click={openCreateForm}
			>
				+ Ajouter
			</button>
		</div>

		{#if $swLoading}
			<div class="flex justify-center py-12">
				<div class="w-6 h-6 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin"></div>
			</div>
		{:else if filteredItems.length === 0}
			<div class="flex flex-col items-center justify-center py-12 gap-3 text-center">
				<div class="text-4xl">{activeTabDef.icon}</div>
				<div>
					<p class="font-medium text-gray-700 dark:text-gray-200">
						{searchQuery ? 'Aucun résultat' : `Aucun ${activeTabDef.label.toLowerCase()} pour l'instant`}
					</p>
					{#if !searchQuery}
						<p class="text-sm text-gray-400 mt-1">Cliquez sur « Ajouter » pour enrichir votre base de connaissances.</p>
					{/if}
				</div>
			</div>
		{:else}
			<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
				{#each filteredItems as item (item.id)}
					<div class="group flex flex-col gap-2 p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:border-gray-300 dark:hover:border-gray-700 hover:shadow-sm transition">
						<!-- Titre + actions -->
						<div class="flex items-start justify-between gap-2">
							<div class="flex-1 min-w-0">
								<div class="font-semibold text-gray-900 dark:text-white truncate">{getItemTitle(item)}</div>
								{#if getItemSubtitle(item)}
									<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5 truncate">{getItemSubtitle(item)}</div>
								{/if}
							</div>
							<div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
								<button
									title="Modifier"
									class="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 hover:text-gray-700 dark:hover:text-white transition text-sm"
									on:click={() => openEditForm(item)}
								>
									✏️
								</button>
								<button
									title="Supprimer"
									class="p-1 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 hover:text-red-500 transition text-sm"
									on:click={() => handleDeleteItem(item)}
								>
									🗑️
								</button>
							</div>
						</div>

						<!-- Preview description -->
						{#if item['description']}
							<p class="text-sm text-gray-600 dark:text-gray-300 line-clamp-2">{item['description']}</p>
						{/if}

						<!-- Tags traits/participants si présents -->
						{#if item['traits'] || item['participants']}
							<div class="flex flex-wrap gap-1 mt-1">
								{#each (Array.isArray(item['traits'] ?? item['participants']) ? (item['traits'] ?? item['participants']) as string[] : []) as tag}
									<span class="px-2 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 text-xs">{tag}</span>
								{/each}
							</div>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>

<!-- Modal création/édition item KB -->
{#if showItemForm}
	<div
		class="fixed inset-0 z-50 flex items-start justify-center bg-black/40 backdrop-blur-sm overflow-y-auto pt-8 pb-8"
		role="dialog"
		aria-modal="true"
		aria-label={editingItem ? `Modifier ${activeTabDef.label}` : `Ajouter ${activeTabDef.label}`}
		on:click|self={closeItemForm}
		on:keydown={(e) => e.key === 'Escape' && closeItemForm()}
	>
		<div class="w-full max-w-lg mx-4 bg-white dark:bg-gray-900 rounded-2xl shadow-2xl p-6 flex flex-col gap-5">
			<div class="flex items-center justify-between">
				<h2 class="text-lg font-bold dark:text-white">
					{activeTabDef.icon} {editingItem ? 'Modifier' : 'Ajouter'} — {activeTabDef.label}
				</h2>
				<button
					class="text-gray-400 hover:text-gray-700 dark:hover:text-white transition text-xl"
					on:click={closeItemForm}
					aria-label="Fermer"
				>
					×
				</button>
			</div>

			<div class="flex flex-col gap-4 max-h-[60vh] overflow-y-auto pr-1">
				{#each Object.entries(activeTabDef.schema) as [fieldKey, fieldDef]}
					<div class="flex flex-col gap-1.5">
						<label class="text-sm font-medium text-gray-700 dark:text-gray-300" for="sw-kb-{activeTab}-{fieldKey}">
							{fieldDef.label}
						</label>
						{#if fieldDef.type === 'textarea'}
							<textarea
								id="sw-kb-{activeTab}-{fieldKey}"
								class="w-full px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 transition resize-none"
								placeholder={fieldDef.placeholder ?? ''}
								rows="3"
								bind:value={formData[fieldKey]}
							/>
						{:else}
							<input
								id="sw-kb-{activeTab}-{fieldKey}"
								type="text"
								class="w-full px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 transition"
								placeholder={fieldDef.placeholder ?? ''}
								bind:value={formData[fieldKey]}
							/>
						{/if}
					</div>
				{/each}
			</div>

			<div class="flex justify-end gap-3 pt-2">
				<button
					class="px-4 py-2 rounded-xl text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
					on:click={closeItemForm}
				>
					Annuler
				</button>
				<button
					id="sw-kb-submit-{activeTab}"
					class="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium transition disabled:opacity-50"
					disabled={$swLoading}
					on:click={handleItemSubmit}
				>
					{$swLoading ? '…' : (editingItem ? 'Enregistrer' : 'Ajouter')}
				</button>
			</div>
		</div>
	</div>
{/if}
