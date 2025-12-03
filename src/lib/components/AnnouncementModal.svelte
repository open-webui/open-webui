<script lang="ts">
  import type { AnnouncementUserView } from '$lib/apis/announcements';

  import DOMPurify from 'dompurify';
  import { marked } from 'marked';

  export let open = false;
  export let announcements: AnnouncementUserView[] = [];
  export let lastSeenAt: number = 0;

  export let onClose: () => void;

  const isNew = (item: AnnouncementUserView) => {
    if (item.is_read === false) return true;
    if (item.created_at && lastSeenAt && item.created_at > lastSeenAt) return true;
    return false;
  };

  const render = (content: string) => {
    try {
      return DOMPurify.sanitize(marked.parse(content || ''));
    } catch (e) {
      console.error(e);
      return content;
    }
  };
</script>

{#if open}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-6">
    <div class="relative w-full max-w-4xl max-h-[85vh] overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-2xl dark:border-gray-800 dark:bg-gray-900">
      <div class="flex items-center justify-between border-b border-gray-100 px-5 py-3 dark:border-gray-800">
        <div>
          <div class="text-3xl font-semibold text-gray-900 dark:text-gray-50">公告</div>
        </div>
        <button
          class="rounded-full p-2 text-gray-500 transition hover:bg-gray-100 hover:text-gray-900 dark:hover:bg-gray-800"
          aria-label="close"
          on:click={onClose}
        >
          ✕
        </button>
      </div>

      <div class="max-h-[60vh] space-y-3 overflow-y-auto px-5 py-4 custom-scroll">
        {#if announcements.length === 0}
          <div class="rounded-xl border border-gray-100 bg-gray-50 px-4 py-3 text-sm text-gray-500 dark:border-gray-800 dark:bg-gray-950 dark:text-gray-300">
            暂无公告
          </div>
        {:else}
          {#each announcements as item}
            <div
              class={`relative rounded-xl px-4 py-3 shadow-sm transition ${
                isNew(item)
                  ? 'bg-amber-50/70 dark:bg-amber-500/10'
                  : 'bg-white dark:bg-gray-900'
              }`}
            >
              {#if isNew(item)}
                <span class="absolute right-3 top-3 rounded-full bg-amber-500 px-2 py-0.5 text-[10px] font-semibold uppercase text-white shadow-sm">新</span>
              {/if}
              <div class="flex flex-wrap items-center gap-2 justify-between">
                <div class="flex items-center gap-2">
                  <div class="text-xl font-bold text-gray-900 dark:text-gray-50">{item.title}</div>
                  {#if item.status !== 'active'}
                    <span class="rounded-full bg-gray-200 px-2 py-0.5 text-[10px] font-semibold text-gray-600 dark:bg-gray-800 dark:text-gray-300">
                      {item.status}
                    </span>
                  {/if}
                </div>
                <div class="text-xs text-gray-500 dark:text-gray-400">
                  {`发布于 ${new Date(item.created_at / 1_000_000).toLocaleString([], {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    hour12: false
                  })}`}
                </div>
              </div>
              <div class="prose prose-sm mt-2 max-w-none text-gray-800 dark:prose-invert dark:text-gray-100">
                {@html render(item.content)}
              </div>
            </div>
          {/each}
        {/if}
      </div>

      <div class="flex items-center justify-end gap-3 border-t border-gray-100 px-5 py-3 dark:border-gray-800">
        <button
          class="rounded-xl border border-gray-200 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800"
          on:click={onClose}
        >
          关闭
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .custom-scroll::-webkit-scrollbar {
    width: 8px;
  }
  .custom-scroll::-webkit-scrollbar-thumb {
    background: rgba(0, 0, 0, 0.1);
    border-radius: 999px;
  }
</style>
