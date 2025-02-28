<script lang="ts">
  import { getContext, tick } from 'svelte';
  const i18n = getContext('i18n');

  import Tooltip from '$lib/components/common/Tooltip.svelte';
  import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
  import Cog6 from '$lib/components/icons/Cog6.svelte';
  import AddConnectionModal from '$lib/components/AddConnectionModal.svelte';



  interface Props {
    onDelete?: any;
    onSubmit?: any;
    pipeline?: boolean;
    url?: string;
    key?: string;
    config?: any;
  }

  let {
    onDelete = () => {},
    onSubmit = () => {},
    pipeline = false,
    url = $bindable(''),
    key = $bindable(''),
    config = $bindable({})
  }: Props = $props();

  let showConfigModal = $state(false);
</script>

<AddConnectionModal
  connection={{
    url,
    key,
    config
  }}
  direct
  edit
  {onDelete}
  onSubmit={(connection) => {
    url = connection.url;
    key = connection.key;
    config = connection.config;
    onSubmit(connection);
  }}
  bind:show={showConfigModal}
/>

<div class="flex w-full gap-2 items-center">
  <Tooltip
    className="w-full relative"
    content={$i18n.t(`WebUI will make requests to "{{url}}/chat/completions"`, {
      url
    })}
    placement="top-start"
  >
    {#if !(config?.enable ?? true)}
      <div class="absolute top-0 bottom-0 left-0 right-0 opacity-60 bg-white dark:bg-gray-900 z-10"></div>
    {/if}
    <div class="flex w-full">
      <div class="flex-1 relative">
        <input
          class=" outline-hidden w-full bg-transparent"
          class:pr-8={pipeline}
          autocomplete="off"
          placeholder={$i18n.t('API Base URL')}
          bind:value={url}
        />
      </div>

      <SensitiveInput
        inputClassName=" outline-hidden bg-transparent w-full"
        placeholder={$i18n.t('API Key')}
        bind:value={key}
      />
    </div>
  </Tooltip>

  <div class="flex gap-1">
    <Tooltip
      className="self-start"
      content={$i18n.t('Configure')}
    >
      <button
        class="self-center p-1 bg-transparent hover:bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-850 rounded-lg transition"
        type="button"
        onclick={() => {
          showConfigModal = true;
        }}
      >
        <Cog6 />
      </button>
    </Tooltip>
  </div>
</div>
