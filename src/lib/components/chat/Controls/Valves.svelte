<script lang="ts">
  import { run, preventDefault } from 'svelte/legacy';

  import { toast } from 'svelte-sonner';

  import { config, functions, models, settings, tools, user } from '$lib/stores';
  import { createEventDispatcher, onMount, getContext, tick } from 'svelte';

  import {
    getUserValvesSpecById as getToolUserValvesSpecById,
    getUserValvesById as getToolUserValvesById,
    updateUserValvesById as updateToolUserValvesById,
    getTools
  } from '$lib/apis/tools';
  import {
    getUserValvesSpecById as getFunctionUserValvesSpecById,
    getUserValvesById as getFunctionUserValvesById,
    updateUserValvesById as updateFunctionUserValvesById,
    getFunctions
  } from '$lib/apis/functions';

  import Tooltip from '$lib/components/common/Tooltip.svelte';
  import Spinner from '$lib/components/common/Spinner.svelte';
  import Valves from '$lib/components/common/Valves.svelte';

  const dispatch = createEventDispatcher();

  const i18n = getContext('i18n');

  interface Props {
    show?: boolean;
  }

  let { show = false }: Props = $props();

  let tab = $state('tools');
  let selectedId = $state('');

  let loading = $state(false);

  let valvesSpec = $state(null);
  let valves = $state({});

  let debounceTimer;

  const debounceSubmitHandler = async () => {
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }

    // Set a new timer
    debounceTimer = setTimeout(() => {
      submitHandler();
    }, 500); // 0.5 second debounce
  };

  const getUserValves = async () => {
    loading = true;
    if (tab === 'tools') {
      valves = await getToolUserValvesById(localStorage.token, selectedId);
      valvesSpec = await getToolUserValvesSpecById(localStorage.token, selectedId);
    } else if (tab === 'functions') {
      valves = await getFunctionUserValvesById(localStorage.token, selectedId);
      valvesSpec = await getFunctionUserValvesSpecById(localStorage.token, selectedId);
    }

    if (valvesSpec) {
      // Convert array to string
      for (const property in valvesSpec.properties) {
        if (valvesSpec.properties[property]?.type === 'array') {
          valves[property] = (valves[property] ?? []).join(',');
        }
      }
    }

    loading = false;
  };

  const submitHandler = async () => {
    if (valvesSpec) {
      // Convert string to array
      for (const property in valvesSpec.properties) {
        if (valvesSpec.properties[property]?.type === 'array') {
          valves[property] = (valves[property] ?? '').split(',').map((v) => v.trim());
        }
      }

      if (tab === 'tools') {
        const res = await updateToolUserValvesById(localStorage.token, selectedId, valves).catch(
          (error) => {
            toast.error(`${error}`);
            return null;
          }
        );

        if (res) {
          toast.success($i18n.t('Valves updated'));
          valves = res;
        }
      } else if (tab === 'functions') {
        const res = await updateFunctionUserValvesById(
          localStorage.token,
          selectedId,
          valves
        ).catch((error) => {
          toast.error(`${error}`);
          return null;
        });

        if (res) {
          toast.success($i18n.t('Valves updated'));
          valves = res;
        }
      }
    }
  };




  const init = async () => {
    loading = true;

    if ($functions === null) {
      functions.set(await getFunctions(localStorage.token));
    }
    if ($tools === null) {
      tools.set(await getTools(localStorage.token));
    }

    loading = false;
  };
  run(() => {
    if (tab) {
      selectedId = '';
    }
  });
  run(() => {
    if (selectedId) {
      getUserValves();
    }
  });
  run(() => {
    if (show) {
      init();
    }
  });
</script>

{#if show && !loading}
  <form
    class="flex flex-col h-full justify-between space-y-3 text-sm"
    onsubmit={preventDefault(() => {
      submitHandler();
      dispatch('save');
    })}
  >
    <div class="flex flex-col">
      <div class="space-y-1">
        <div class="flex gap-2">
          <div class="flex-1">
            <select
              class="  w-full rounded-sm text-xs py-2 px-1 bg-transparent outline-hidden"
              placeholder="Select"
              bind:value={tab}
            >
              <option
                class="bg-gray-100 dark:bg-gray-800"
                value="tools"
              >{$i18n.t('Tools')}</option>
              <option
                class="bg-gray-100 dark:bg-gray-800"
                value="functions"
              >{$i18n.t('Functions')}</option>
            </select>
          </div>

          <div class="flex-1">
            <select
              class="w-full rounded-sm py-2 px-1 text-xs bg-transparent outline-hidden"
              bind:value={selectedId}
              onchange={async () => {
                await tick();
              }}
            >
              {#if tab === 'tools'}
                <option
                  class="bg-gray-100 dark:bg-gray-800"
                  disabled
                  selected
                  value=""
                >{$i18n.t('Select a tool')}</option>

                {#each $tools as tool, toolIdx}
                  <option
                    class="bg-gray-100 dark:bg-gray-800"
                    value={tool.id}
                  >{tool.name}</option>
                {/each}
              {:else if tab === 'functions'}
                <option
                  class="bg-gray-100 dark:bg-gray-800"
                  disabled
                  selected
                  value=""
                >{$i18n.t('Select a function')}</option>

                {#each $functions as func, funcIdx}
                  <option
                    class="bg-gray-100 dark:bg-gray-800"
                    value={func.id}
                  >{func.name}</option>
                {/each}
              {/if}
            </select>
          </div>
        </div>
      </div>

      {#if selectedId}
        <hr class="dark:border-gray-800 my-1 w-full" />

        <div class="my-2 text-xs">
          {#if !loading}
            <Valves
              {valvesSpec}
              bind:valves
              on:change={() => {
                debounceSubmitHandler();
              }}
            />
          {:else}
            <Spinner className="size-5" />
          {/if}
        </div>
      {/if}
    </div>
  </form>
{:else}
  <Spinner className="size-4" />
{/if}
