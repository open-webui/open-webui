<script lang="ts">
	import { editChapter, swLoading, editorMode, chapters, activeKB } from '$lib/stores/sw';
	import { toast } from 'svelte-sonner';
	import {
		Save,
		Sparkles,
		Wand2,
		Type,
		BookOpen,
		Maximize2,
		Minimize2,
		Search,
		LayoutGrid,
		Layout,
		Download,
		FileText,
		ChevronRight,
		CheckCircle2
	} from 'lucide-svelte';
	import { onMount, tick } from 'svelte';
	import { fade, slide, fly } from 'svelte/transition';
	import ChapterKBPanel from './ChapterKBPanel.svelte';
	import { showSidebar } from '$lib/stores';

	export let chapter;
	export let onSelect: (id: string) => void = () => {};
	export let onSave: () => void = () => {};

	let title = '';
	let content = '';
	let status = 'draft';
	let lastSavedContent = '';
	let saveTimeout;
	let isSaving = false;

	$: if (chapter) {
		title = chapter.title;
		content = chapter.content || '';
		status = chapter.status;
		lastSavedContent = content;
	}

	async function handleSave() {
		if (!chapter) return;
		const token = localStorage.getItem('token');
		if (!token) return;

		isSaving = true;
		const updated = await editChapter(token, chapter.id, {
			title,
			content,
			status
		});

		if (updated) {
			lastSavedContent = content;
			onSave();
		}
		isSaving = false;
	}

	function handleContentChange(e) {
		clearTimeout(saveTimeout);
		saveTimeout = setTimeout(handleSave, 2000);
	}

	function runTool(tool: string) {
		const command = `/${tool} (sur le chapitre: ${title})`;
		toast.info(`Utilisez la commande ${command} dans le chat pour obtenir de l'aide.`);
	}

	function toggleMode(mode: 'full' | 'focus' | 'research' | 'outline') {
		editorMode.set(mode);
		if (mode === 'focus') {
			showSidebar.set(false);
		}
	}

	async function exportDoc(type: 'pdf' | 'md') {
		toast.promise(
			(async () => {
				const { exportManuscript } = await import('./utils/export');
				await exportManuscript(type === 'pdf' ? 'formatageLivre' : 'markdown');
			})(),
			{
				loading: 'Génération de l\'export...',
				success: 'Export terminé !',
				error: 'Erreur lors de l\'export.'
			}
		);
	}

	$: isDirty = content !== lastSavedContent;
</script>

<div class="flex h-full bg-white dark:bg-gray-950 overflow-hidden relative">
	<!-- Main Content Area -->
	<div class="flex-1 flex flex-col min-w-0 transition-all duration-500 ease-in-out h-full overflow-hidden">
		<!-- Top Bar -->
		<div class="px-6 py-3 flex justify-between items-center border-b dark:border-gray-800 bg-white/50 dark:bg-gray-950/50 backdrop-blur-md z-10">
			<div class="flex-1 flex items-center gap-4">
				{#if $editorMode !== 'outline'}
					<input
						type="text"
						bind:value={title}
						on:blur={handleSave}
						class="bg-transparent text-lg font-bold focus:outline-none dark:text-gray-100 flex-1 truncate"
						placeholder="Titre du chapitre..."
					/>
				{:else}
					<h2 class="text-lg font-bold dark:text-gray-100">Vue d'ensemble du manuscrit</h2>
				{/if}

				<div class="flex items-center gap-1 bg-gray-100 dark:bg-gray-900 p-1 rounded-xl">
					<button
						class="p-1.5 rounded-lg transition-all {$editorMode === 'full' ? 'bg-white dark:bg-gray-800 shadow-sm text-blue-600' : 'text-gray-400 hover:text-gray-600'}"
						on:click={() => toggleMode('full')}
						title="Mode Standard"
					>
						<Layout size={16} />
					</button>
					<button
						class="p-1.5 rounded-lg transition-all {$editorMode === 'focus' ? 'bg-white dark:bg-gray-800 shadow-sm text-blue-600' : 'text-gray-400 hover:text-gray-600'}"
						on:click={() => toggleMode('focus')}
						title="Mode Focus"
					>
						<Maximize2 size={16} />
					</button>
					<button
						class="p-1.5 rounded-lg transition-all {$editorMode === 'research' ? 'bg-white dark:bg-gray-800 shadow-sm text-blue-600' : 'text-gray-400 hover:text-gray-600'}"
						on:click={() => toggleMode('research')}
						title="Mode Recherche (KB)"
					>
						<Search size={16} />
					</button>
					<button
						class="p-1.5 rounded-lg transition-all {$editorMode === 'outline' ? 'bg-white dark:bg-gray-800 shadow-sm text-blue-600' : 'text-gray-400 hover:text-gray-600'}"
						on:click={() => toggleMode('outline')}
						title="Vue Grid / Outline"
					>
						<LayoutGrid size={16} />
					</button>
				</div>
			</div>

			<div class="flex items-center gap-3">
				<!-- Status & Save info -->
				{#if $editorMode !== 'outline'}
					<div class="hidden sm:flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded-md {isSaving ? 'text-amber-500' : isDirty ? 'text-gray-400' : 'text-emerald-500'}">
						{#if isSaving}
							<span class="animate-pulse">Sauvegarde...</span>
						{:else if !isDirty}
							<CheckCircle2 size={12} />
							<span>À jour</span>
						{:else}
							<span>Modifié</span>
						{/if}
					</div>

					<select
						bind:value={status}
						on:change={handleSave}
						class="text-[10px] uppercase font-bold tracking-tighter bg-gray-50 dark:bg-gray-900 border dark:border-gray-800 rounded-lg px-2 py-1 outline-none dark:text-gray-300"
					>
						<option value="draft">Brouillon</option>
						<option value="in-progress">En cours</option>
						<option value="completed">Terminé</option>
					</select>
				{/if}

				<!-- Export Menu -->
				<div class="flex items-center gap-1 border-l dark:border-gray-800 pl-3">
					<button
						class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 transition-colors"
						on:click={() => exportDoc('pdf')}
						title="Exporter en PDF"
					>
						<FileText size={18} />
					</button>
					<button
						class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 transition-colors"
						on:click={() => exportDoc('md')}
						title="Exporter en Markdown"
					>
						<Download size={18} />
					</button>
				</div>
			</div>
		</div>

		<!-- Editor Area -->
		<div class="flex-1 overflow-y-auto relative p-6 md:p-12 lg:p-20 flex justify-center custom-scrollbar">
			{#if $editorMode === 'outline'}
				<div class="w-full max-w-6xl grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" in:fade>
					{#each $chapters.sort((a,b) => a.order - b.order) as ch}
						<!-- svelte-ignore a11y-click-events-have-key-events -->
						<div 
							class="p-5 rounded-2xl border dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50 hover:border-blue-500/50 dark:hover:border-blue-500/50 transition-all group flex flex-col h-48 cursor-pointer"
							on:click={() => {
								onSelect(ch.id);
								toggleMode('full');
							}}
						>
							<div class="flex justify-between items-start mb-3">
								<h3 class="font-bold text-sm dark:text-gray-100 truncate flex-1 pr-2">{ch.title}</h3>
								<span class="text-[9px] uppercase px-1.5 py-0.5 rounded bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400">{ch.status}</span>
							</div>
							<p class="text-[11px] leading-relaxed text-gray-500 dark:text-gray-400 line-clamp-5 flex-1 italic">
								{ch.content || "Chapitre vide..."}
							</p>
							<div class="mt-4 flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
								<button class="text-[10px] font-bold text-blue-500 uppercase">Éditer le chapitre</button>
								<ChevronRight size={12} class="text-blue-500" />
							</div>
						</div>
					{/each}
				</div>
			{:else}
				<div class="w-full transition-all duration-700 {$editorMode === 'focus' ? 'max-w-3xl' : 'max-w-4xl'}" in:fade>
					<textarea
						bind:value={content}
						on:input={handleContentChange}
						placeholder="Il était une fois..."
						class="w-full h-full min-h-[75vh] bg-transparent resize-none focus:outline-none text-xl leading-loose dark:text-gray-200 font-serif selection:bg-blue-100 dark:selection:bg-blue-900/40"
					/>
				</div>
			{/if}
		</div>

		<!-- Floating Tools Toolbar (only if not outline) -->
		{#if $editorMode !== 'outline'}
			<div
				class="fixed bottom-10 left-1/2 -translate-x-1/2 flex items-center gap-1 p-1 bg-white/60 dark:bg-gray-900/60 backdrop-blur-xl rounded-2xl border shadow-2xl dark:border-gray-700 z-50 transition-all hover:scale-105 active:scale-95"
				in:fly={{ y: 20, duration: 500 }}
			>
				<button 
					class="flex items-center gap-2 px-4 py-2.5 rounded-xl hover:bg-white dark:hover:bg-gray-800 transition-all text-xs font-bold uppercase tracking-tight" 
					on:click={() => runTool('brainstorm')}
					title="Générer des idées pour ce chapitre"
				>
					<Sparkles size={16} class="text-amber-500" />
					<span class="dark:text-gray-200">Brainstorm</span>
				</button>
				<div class="w-px h-6 bg-gray-200 dark:bg-gray-700 mx-1"></div>
				<button 
					class="flex items-center gap-2 px-4 py-2.5 rounded-xl hover:bg-white dark:hover:bg-gray-800 transition-all text-xs font-bold uppercase tracking-tight" 
					on:click={() => runTool('coherence')}
					title="Vérifier la cohérence avec la Knowledge Base"
				>
					<Wand2 size={16} class="text-blue-500" />
					<span class="dark:text-gray-200">Cohérence</span>
				</button>
				<div class="w-px h-6 bg-gray-200 dark:bg-gray-700 mx-1"></div>
				<button 
					class="flex items-center gap-2 px-4 py-2.5 rounded-xl hover:bg-white dark:hover:bg-gray-800 transition-all text-xs font-bold uppercase tracking-tight" 
					on:click={() => runTool('dialogue')}
					title="Aide à la rédaction des dialogues"
				>
					<Type size={16} class="text-emerald-500" />
					<span class="dark:text-gray-200">Dialogue</span>
				</button>
				<div class="w-px h-6 bg-gray-200 dark:bg-gray-700 mx-1"></div>
				<button 
					class="flex items-center gap-2 px-4 py-2.5 rounded-xl hover:bg-white dark:hover:bg-gray-800 transition-all text-xs font-bold uppercase tracking-tight" 
					on:click={() => runTool('outline')}
					title="Suggérer une structure pour la suite"
				>
					<BookOpen size={16} class="text-purple-500" />
					<span class="dark:text-gray-200">Structure</span>
				</button>
			</div>
		{/if}
	</div>

	<!-- Side Panel for Research Mode -->
	{#if $editorMode === 'research'}
		<div class="h-full border-l dark:border-gray-800 z-20" in:fly={{ x: 200, duration: 400 }} out:fly={{ x: 200, duration: 300 }}>
			<ChapterKBPanel />
		</div>
	{/if}
</div>

<style>
	textarea {
		font-family: 'EB Garamond', 'Georgia', 'Cambria', 'Times New Roman', Times, serif;
	}

	.custom-scrollbar::-webkit-scrollbar {
		width: 6px;
	}
	.custom-scrollbar::-webkit-scrollbar-track {
		background: transparent;
	}
	.custom-scrollbar::-webkit-scrollbar-thumb {
		background: #8882;
		border-radius: 10px;
	}
</style>
