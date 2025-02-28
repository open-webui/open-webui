<script lang="ts">
  import { run } from 'svelte/legacy';

  import { getContext, createEventDispatcher } from 'svelte';
  const i18n = getContext('i18n');

  import dayjs from '$lib/dayjs';
  import duration from 'dayjs/plugin/duration';
  import relativeTime from 'dayjs/plugin/relativeTime';

  dayjs.extend(duration);
  dayjs.extend(relativeTime);

  async function loadLocale(locales) {
    for (const locale of locales) {
      try {
        dayjs.locale(locale);
        break; // Stop after successfully loading the first available locale
      } catch (error) {
        console.error(`Could not load locale '${locale}':`, error);
      }
    }
  }


  const dispatch = createEventDispatcher();

  import { slide } from 'svelte/transition';
  import { quintOut } from 'svelte/easing';

  import ChevronUp from '../icons/ChevronUp.svelte';
  import ChevronDown from '../icons/ChevronDown.svelte';
  import Spinner from './Spinner.svelte';



  interface Props {
    open?: boolean;
    id?: string;
    className?: string;
    buttonClassName?: string;
    title?: any;
    attributes?: any;
    grow?: boolean;
    disabled?: boolean;
    hide?: boolean;
    children?: import('svelte').Snippet;
    content?: import('svelte').Snippet;
  }

  let {
    open = $bindable(false),
    id = '',
    className = '',
    buttonClassName = 'w-fit text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition',
    title = null,
    attributes = null,
    grow = false,
    disabled = false,
    hide = false,
    children,
    content
  }: Props = $props();
  // Assuming $i18n.languages is an array of language codes
  run(() => {
    loadLocale($i18n.languages);
  });
  run(() => {
    dispatch('change', open);
  });
</script>

<div
  {id}
  class={className}
>
  {#if title !== null}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div
      class="{buttonClassName} cursor-pointer"
      onpointerup={() => {
        if (!disabled) {
          open = !open;
        }
      }}
    >
      <div
        class=" w-full font-medium flex items-center justify-between gap-2"
        class:shimmer={attributes?.done &&
          attributes?.done !== 'true'}
      >
        {#if attributes?.done && attributes?.done !== 'true'}
          <div>
            <Spinner className="size-4" />
          </div>
        {/if}

        <div class="">
          {#if attributes?.type === 'reasoning'}
            {#if attributes?.done === 'true' && attributes?.duration}
              {#if attributes.duration < 60}
                {$i18n.t('Thought for {{DURATION}} seconds', {
                  DURATION: attributes.duration
                })}
              {:else}
                {$i18n.t('Thought for {{DURATION}}', {
                  DURATION: dayjs.duration(attributes.duration, 'seconds').humanize()
                })}
              {/if}
            {:else}
              {$i18n.t('Thinking...')}
            {/if}
          {:else if attributes?.type === 'code_interpreter'}
            {#if attributes?.done === 'true'}
              {$i18n.t('Analyzed')}
            {:else}
              {$i18n.t('Analyzing...')}
            {/if}
          {:else}
            {title}
          {/if}
        </div>

        <div class="flex self-center translate-y-[1px]">
          {#if open}
            <ChevronUp
              className="size-3.5"
              strokeWidth="3.5"
            />
          {:else}
            <ChevronDown
              className="size-3.5"
              strokeWidth="3.5"
            />
          {/if}
        </div>
      </div>
    </div>
  {:else}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div
      class="{buttonClassName} cursor-pointer"
      onpointerup={() => {
        if (!disabled) {
          open = !open;
        }
      }}
    >
      <div>
        {@render children?.()}

        {#if grow}
          {#if open && !hide}
            <div
              onpointerup={(e) => {
                e.stopPropagation();
              }}
              transition:slide={{ duration: 300, easing: quintOut, axis: 'y' }}
            >
              {@render content?.()}
            </div>
          {/if}
        {/if}
      </div>
    </div>
  {/if}

  {#if !grow}
    {#if open && !hide}
      <div transition:slide={{ duration: 300, easing: quintOut, axis: 'y' }}>
        {@render content?.()}
      </div>
    {/if}
  {/if}
</div>
