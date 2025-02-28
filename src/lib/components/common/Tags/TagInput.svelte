<script lang="ts">
  import { createEventDispatcher, getContext } from 'svelte';
  import { tags } from '$lib/stores';
  import { toast } from 'svelte-sonner';
  const dispatch = createEventDispatcher();

  const i18n = getContext('i18n');

  interface Props {
    label?: string;
  }

  let { label = '' }: Props = $props();
  let showTagInput = $state(false);
  let tagName = $state('');

  const addTagHandler = async () => {
    tagName = tagName.trim();
    if (tagName !== '') {
      dispatch('add', tagName);
      tagName = '';
      showTagInput = false;
    } else {
      toast.error($i18n.t(`Invalid Tag`));
    }
  };
</script>

<div
  class="px-0.5 flex"
  class:flex-row-reverse={showTagInput}
>
  {#if showTagInput}
    <div class="flex items-center">
      <input
        class=" px-2 cursor-pointer self-center text-xs h-fit bg-transparent outline-hidden line-clamp-1 w-[6.5rem]"
        list="tagOptions"
        placeholder={$i18n.t('Add a tag')}
        bind:value={tagName}
        onkeydown={(event) => {
          if (event.key === 'Enter') {
            addTagHandler();
          }
        }}
      />
      <datalist id="tagOptions">
        {#each $tags as tag}
          <option value={tag.name}></option>
        {/each}
      </datalist>

      <button
        aria-label={$i18n.t('Save Tag')}
        type="button"
        onclick={addTagHandler}
      >
        <svg
          class="w-3 h-3"
          fill="currentColor"
          stroke-width="2"
          viewBox="0 0 16 16"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            clip-rule="evenodd"
            d="M12.416 3.376a.75.75 0 0 1 .208 1.04l-5 7.5a.75.75 0 0 1-1.154.114l-3-3a.75.75 0 0 1 1.06-1.06l2.353 2.353 4.493-6.74a.75.75 0 0 1 1.04-.207Z"
            fill-rule="evenodd"
          />
        </svg>
      </button>
    </div>
  {/if}

  <button
    class=" cursor-pointer self-center p-0.5 flex h-fit items-center dark:hover:bg-gray-700 rounded-full transition border dark:border-gray-600 border-dashed"
    aria-label={$i18n.t('Add Tag')}
    type="button"
    onclick={() => {
      showTagInput = !showTagInput;
    }}
  >
    <div class=" m-auto self-center">
      <svg
        class="w-3 h-3 transition-all transform"
        class:rotate-45={showTagInput}
        fill="currentColor"
        viewBox="0 0 16 16"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path d="M8.75 3.75a.75.75 0 0 0-1.5 0v3.5h-3.5a.75.75 0 0 0 0 1.5h3.5v3.5a.75.75 0 0 0 1.5 0v-3.5h3.5a.75.75 0 0 0 0-1.5h-3.5v-3.5Z" />
      </svg>
    </div>
  </button>

  {#if label && !showTagInput}
    <span class="text-xs pl-2 self-center">{label}</span>
  {/if}
</div>
