<script lang="ts">
  import Switch from '$lib/components/common/Switch.svelte';
  import Textarea from '$lib/components/common/Textarea.svelte';
  import Tooltip from '$lib/components/common/Tooltip.svelte';
  import EllipsisVertical from '$lib/components/icons/EllipsisVertical.svelte';
  import XMark from '$lib/components/icons/XMark.svelte';
  import PencilSolid from '$lib/components/icons/PencilSolid.svelte';
  import Sortable from 'sortablejs';
  import { getContext } from 'svelte';
  import { config } from '$lib/stores';

  const i18n = getContext('i18n');

  export let banners: any[] = [];

  let sortable: any = null;
  let bannerListElement: HTMLDivElement | null = null;

  // reactive UI language code
  $: langCode = $i18n?.language?.split('-')[0] || 'en';

  // dynamic languages from config
  $: LANGS = Array.isArray($config.features.translation_languages)
    ? [...new Set([...$config.features.translation_languages, langCode])]
    : [langCode, 'en'];

  // contentObjs stores parsed content objects keyed by banner.id
  let contentObjs: Record<string, Record<string, string>> = {};

  // Create a helper function to get/set content safely
  function getContent(bannerId: string, lang: string): string {
    ensureContentStructure(bannerId);
    return contentObjs[bannerId][lang] || '';
  }

  function setContent(bannerId: string, lang: string, value: string) {
    ensureContentStructure(bannerId);
    contentObjs[bannerId][lang] = value;
    contentObjs = { ...contentObjs };
    
    // Update the corresponding banner
    const bannerIndex = banners.findIndex(b => b.id === bannerId);
    if (bannerIndex !== -1) {
      banners[bannerIndex].content = safeStringify(contentObjs[bannerId]);
      banners = [...banners];
      
      // Sync to modal if open
      if (showBannerModal && editingBannerIndex === bannerIndex) {
        newBanner.content[lang] = value;
        newBanner = { ...newBanner };
      }
    }
  }

  function ensureContentStructure(bannerId: string) {
    if (!contentObjs[bannerId]) {
      const banner = banners.find(b => b.id === bannerId);
      contentObjs[bannerId] = banner ? parseContentToObj(banner.content) : {};
    }
    
    // Ensure all required languages exist
    const allLangs = [...new Set([...LANGS, langCode])];
    for (const lang of allLangs) {
      if (!contentObjs[bannerId][lang]) {
        contentObjs[bannerId][lang] = '';
      }
    }
  }

  // Initialize/Sync contentObjs with banners
  $: if (banners && banners.length > 0) {
    for (const b of banners) {
      if (!b) continue;
      const id = b.id ?? (b.id = crypto?.randomUUID ? crypto.randomUUID() : String(Date.now()));
      
      ensureContentStructure(id);
      
      // Sync from banner.content if it has changed
      const currentString = safeStringify(contentObjs[id]);
      const incomingString = typeof b.content === 'string'
        ? b.content
        : safeStringify(parseContentToObj(b.content));
      if (incomingString !== currentString && incomingString !== '{}') {
        contentObjs[id] = parseContentToObj(b.content);
        ensureContentStructure(id); // Re-ensure after parsing
      }
    }

    // remove entries for banners that no longer exist
    const ids = new Set(banners.map((b) => b.id));
    for (const key of Object.keys(contentObjs)) {
      if (!ids.has(key)) delete contentObjs[key];
    }

    initSortable();
  }

  function parseContentToObj(content: any) {
    let parsed: Record<string, string> = {};
    try {
      parsed = typeof content === 'string' ? JSON.parse(content) : { ...content };
    } catch {
      parsed = { de: content || '' };
    }

    // keep current languages and check that LANGS are included
    const allLangs = [...new Set([...LANGS, langCode, ...Object.keys(parsed)])];
    for (const lang of allLangs) {
      if (parsed[lang] == null) parsed[lang] = '';
    }
    return parsed;
  }

  function safeStringify(obj: any) {
    try { return JSON.stringify(obj); } 
    catch { return '{}'; }
  }

  function initSortable() {
    if (sortable) { try { sortable.destroy(); } catch {} sortable = null; }
    if (bannerListElement) {
      sortable = Sortable.create(bannerListElement, {
        animation: 150,
        handle: '.item-handle',
        onUpdate: () => {
          const order = Array.from(bannerListElement!.children)
            .map(ch => (ch as HTMLElement).id.replace('banner-item-', ''));
          banners = order.map(id => banners.find(b => b.id === id));
        }
      });
    }
  }

  let showBannerModal = false;
  let editingBannerIndex: number | null = null;
  let newBanner: { id: string; content: Record<string, string>; workspaces: string[] } = { id: '', content: {}, workspaces: [] };

  function openEditModal(idx: number) {
    editingBannerIndex = idx;
    const b = banners[idx];
    if (!b) return;
    
    const id = b.id;
    const workspaces = b.workspaces || [];
    
    ensureContentStructure(id);
    
    // Copy current contentObjs to newBanner
    newBanner = { 
      id, 
      content: JSON.parse(JSON.stringify(contentObjs[id])), // Deep copy of current state
      workspaces: [...workspaces]
    };
    
    showBannerModal = true;
  }

  function syncModalToInline(changedLang: string) {
    if (editingBannerIndex !== null) {
      const id = banners[editingBannerIndex].id;
      
      ensureContentStructure(id);
      contentObjs[id][changedLang] = newBanner.content[changedLang] || '';
      contentObjs = { ...contentObjs };
      
      // Update banner content
      banners[editingBannerIndex].content = safeStringify(contentObjs[id]);
      banners = [...banners];
    }
  }

  function closeModal() {
    showBannerModal = false;
    editingBannerIndex = null;
    newBanner = { id: '', content: Object.fromEntries(LANGS.map(l => [l, ''])), workspaces:[] };
  }

  function saveModal() {
    const any = Object.values(newBanner.content).some(v => v && v.trim() !== '');
    if (!any) {
      alert('At least one translation is required.');
      return;
    }

    if (!newBanner.content.de?.trim()) {
      const first = Object.values(newBanner.content).find(v => v.trim() !== '');
      if (first) newBanner.content.de = first;
    }

    if (editingBannerIndex != null) {
      banners[editingBannerIndex].content = safeStringify(newBanner.content);
      banners[editingBannerIndex].workspaces = newBanner.workspaces;

      contentObjs[newBanner.id] = { ...newBanner.content };
      contentObjs = { ...contentObjs };
      banners = [...banners];
    }

    closeModal();
  }
</script>

<!-- Draggable banners -->
<div class="flex flex-col gap-3 {banners?.length > 0 ? 'mt-2' : ''}" bind:this={bannerListElement}>
  {#each banners as banner, bannerIdx (banner.id)}
    <div class="flex justify-between items-start -ml-1" id={"banner-item-" + banner.id}>
      <EllipsisVertical className="size-4 cursor-move item-handle" />

      <div class="flex flex-row flex-1 gap-2 items-start">
        <select
          class="w-fit capitalize rounded-xl text-xs bg-transparent outline-hidden pl-1 pr-5"
          bind:value={banner.type}
          required
        >
          {#if banner.type == ''}
            <option value="" selected disabled class="text-gray-900">{$i18n.t('Type')}</option>
          {/if}
          <option value="info" class="text-gray-900">{$i18n.t('Info')}</option>
          <option value="warning" class="text-gray-900">{$i18n.t('Warning')}</option>
          <option value="error" class="text-gray-900">{$i18n.t('Error')}</option>
          <option value="success" class="text-gray-900">{$i18n.t('Success')}</option>
        </select>

        <!-- Use getter/setter approach instead of direct binding -->
        <textarea
          class="mr-2 text-xs w-full bg-transparent outline-hidden resize-none border-0 p-1"
          placeholder={$i18n.t('Content')}
          value={getContent(banner.id, langCode)}
          on:input={(e) => {
            const value = e.target?.value || '';
            setContent(banner.id, langCode, value);
          }}
          rows="2"
        ></textarea>

        <div class="relative -left-2">
          <Tooltip content={$i18n.t('Remember Dismissal')} class="flex h-fit items-center">
            <Switch bind:state={banner.dismissible} />
          </Tooltip>
        </div>
      </div>

      <button class="p-1 text-gray-500 hover:text-yellow-600" type="button" on:click={() => openEditModal(bannerIdx)} title={$i18n.t('Edit')}>
        <PencilSolid />
      </button>

      <button class="pr-3" type="button" on:click={() => { banners.splice(bannerIdx, 1); banners = banners; }}>
        <XMark className={'size-4'} />
      </button>
    </div>
  {/each}
</div>

<!-- Modal -->
{#if showBannerModal}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50">
    <div class="bg-white dark:bg-gray-800 p-4 rounded-md shadow-md w-[90%] max-w-md">
      <div class="flex justify-between dark:text-gray-300 pt-4 pb-1">
        <h2 class="text-sm font-bold mb-2">{$i18n.t('Edit Translations')}</h2>
        <button class="text-xs px-2 py-1" on:click={closeModal}>
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
            <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22z"/>
          </svg>
        </button>
      </div>

      {#each LANGS as lang}
        <div class="mb-2">
          <label class="text-xs font-semibold block mb-1">{lang.toUpperCase()}</label>
          <Textarea
            class="w-full text-sm p-1 border border-gray-300 dark:border-gray-700 rounded"
            bind:value={newBanner.content[lang]}
            placeholder={`Enter ${lang.toUpperCase()} content`}
            maxSize={200}
            on:input={() => syncModalToInline(lang)}
          />
        </div>
      {/each}

      <div class="flex justify-end space-x-2 mt-3">
        <button
          class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
          on:click={saveModal}
        >
          {$i18n.t('Save')}
        </button>
      </div>
    </div>
  </div>
{/if}