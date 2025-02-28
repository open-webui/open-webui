<script lang="ts">
  import { run } from 'svelte/legacy';

  import fileSaver from 'file-saver';
  const { saveAs } = fileSaver;

  import { toast } from 'svelte-sonner';

  import panzoom, { type PanZoom } from 'panzoom';
  import DOMPurify from 'dompurify';

  import { onMount, getContext } from 'svelte';
  const i18n = getContext('i18n');

  import { copyToClipboard } from '$lib/utils';

  import DocumentDuplicate from '../icons/DocumentDuplicate.svelte';
  import Tooltip from './Tooltip.svelte';
  import Clipboard from '../icons/Clipboard.svelte';
  import Reset from '../icons/Reset.svelte';
  import ArrowDownTray from '../icons/ArrowDownTray.svelte';

  interface Props {
    className?: string;
    svg?: string;
    content?: string;
  }

  let { className = '', svg = '', content = '' }: Props = $props();

  let instance: PanZoom = $state();

  let sceneParentElement: HTMLElement = $state();
  let sceneElement: HTMLElement = $state();

  run(() => {
    if (sceneElement) {
      instance = panzoom(sceneElement, {
        bounds: true,
        boundsPadding: 0.1,

        zoomSpeed: 0.065
      });
    }
  });
  const resetPanZoomViewport = () => {
    instance.moveTo(0, 0);
    instance.zoomAbs(0, 0, 1);
    console.log(instance.getTransform());
  };

  const downloadAsSVG = () => {
    const svgBlob = new Blob([svg], { type: 'image/svg+xml' });
    saveAs(svgBlob, `diagram.svg`);
  };
</script>

<div
  bind:this={sceneParentElement}
  class="relative {className}"
>
  <div
    bind:this={sceneElement}
    class="flex h-full max-h-full justify-center items-center"
  >
    {@html svg}
  </div>

  {#if content}
    <div class=" absolute top-1 right-1">
      <div class="flex gap-1">
        <Tooltip content={$i18n.t('Download as SVG')}>
          <button
            class="p-1.5 rounded-lg border border-gray-100 dark:border-none dark:bg-gray-850 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
            onclick={() => {
              downloadAsSVG();
            }}
          >
            <ArrowDownTray className=" size-4" />
          </button>
        </Tooltip>

        <Tooltip content={$i18n.t('Reset view')}>
          <button
            class="p-1.5 rounded-lg border border-gray-100 dark:border-none dark:bg-gray-850 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
            onclick={() => {
              resetPanZoomViewport();
            }}
          >
            <Reset className=" size-4" />
          </button>
        </Tooltip>

        <Tooltip content={$i18n.t('Copy to clipboard')}>
          <button
            class="p-1.5 rounded-lg border border-gray-100 dark:border-none dark:bg-gray-850 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
            onclick={() => {
              copyToClipboard(content);
              toast.success($i18n.t('Copied to clipboard'));
            }}
          >
            <Clipboard
              className=" size-4"
              strokeWidth="1.5"
            />
          </button>
        </Tooltip>
      </div>
    </div>
  {/if}
</div>
