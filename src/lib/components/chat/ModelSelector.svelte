<script lang="ts">
  import { run } from 'svelte/legacy';

  import { models, showSettings, settings, user, mobile, config } from '$lib/stores';
  import { onMount, tick, getContext } from 'svelte';
  import { toast } from 'svelte-sonner';
  import Selector from './ModelSelector/Selector.svelte';
  import Tooltip from '../common/Tooltip.svelte';

  import { updateUserSettings } from '$lib/apis/users';
  const i18n = getContext('i18n');


  interface Props {
    selectedModels?: any;
    disabled?: boolean;
    showSetDefault?: boolean;
  }

  let { selectedModels = $bindable(['']), disabled = false, showSetDefault = true }: Props = $props();

  const saveDefaultModel = async () => {
    const hasEmptyModel = selectedModels.filter((it) => it === '');
    if (hasEmptyModel.length) {
      toast.error($i18n.t('Choose a model before saving...'));
      return;
    }
    settings.set({ ...$settings, models: selectedModels });
    await updateUserSettings(localStorage.token, { ui: $settings });

    toast.success($i18n.t('Default model updated'));
  };

  run(() => {
    if (selectedModels.length > 0 && $models.length > 0) {
      selectedModels = selectedModels.map((model) =>
        $models.map((m) => m.id).includes(model) ? model : ''
      );
    }
  });
</script>

<div class="flex flex-col w-full items-start">
  {#each selectedModels as selectedModel, selectedModelIdx}
    <div class="flex w-full max-w-fit">
      <div class="overflow-hidden w-full">
        <div class="mr-1 max-w-full">
          <Selector
            id={`${selectedModelIdx}`}
            items={$models.map((model) => ({
              value: model.id,
              label: model.name,
              model: model
            }))}
            placeholder={$i18n.t('Select a model')}
            showTemporaryChatControl={$user.role === 'user'
              ? ($user?.permissions?.chat?.temporary ?? true)
              : true}
            bind:value={selectedModel}
          />
        </div>
      </div>

      {#if selectedModelIdx === 0}
        <div class="  self-center mx-1 disabled:text-gray-600 disabled:hover:text-gray-600 -translate-y-[0.5px]">
          <Tooltip content={$i18n.t('Add Model')}>
            <button
              class=" "
              aria-label="Add Model"
              {disabled}
              onclick={() => {
                selectedModels = [...selectedModels, ''];
              }}
            >
              <svg
                class="size-3.5"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                viewBox="0 0 24 24"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M12 6v12m6-6H6"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
            </button>
          </Tooltip>
        </div>
      {:else}
        <div class="  self-center mx-1 disabled:text-gray-600 disabled:hover:text-gray-600 -translate-y-[0.5px]">
          <Tooltip content={$i18n.t('Remove Model')}>
            <button
              aria-label="Remove Model"
              {disabled}
              onclick={() => {
                selectedModels.splice(selectedModelIdx, 1);
                selectedModels = selectedModels;
              }}
            >
              <svg
                class="size-3"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                viewBox="0 0 24 24"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M19.5 12h-15"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
            </button>
          </Tooltip>
        </div>
      {/if}
    </div>
  {/each}
</div>

{#if showSetDefault}
  <div class=" absolute text-left mt-[1px] ml-1 text-[0.7rem] text-gray-500 font-primary">
    <button onclick={saveDefaultModel}> {$i18n.t('Set as default')}</button>
  </div>
{/if}
