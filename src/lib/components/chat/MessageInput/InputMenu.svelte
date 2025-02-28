<script lang="ts">
  import { run } from 'svelte/legacy';

  import { DropdownMenu } from 'bits-ui';
  import { flyAndScale } from '$lib/utils/transitions';
  import { getContext, onMount, tick } from 'svelte';

  import { config, user, tools as _tools, mobile } from '$lib/stores';
  import { createPicker } from '$lib/utils/google-drive-picker';

  import { getTools } from '$lib/apis/tools';

  import Dropdown from '$lib/components/common/Dropdown.svelte';
  import Tooltip from '$lib/components/common/Tooltip.svelte';
  import DocumentArrowUpSolid from '$lib/components/icons/DocumentArrowUpSolid.svelte';
  import Switch from '$lib/components/common/Switch.svelte';
  import GlobeAltSolid from '$lib/components/icons/GlobeAltSolid.svelte';
  import WrenchSolid from '$lib/components/icons/WrenchSolid.svelte';
  import CameraSolid from '$lib/components/icons/CameraSolid.svelte';
  import PhotoSolid from '$lib/components/icons/PhotoSolid.svelte';
  import CommandLineSolid from '$lib/components/icons/CommandLineSolid.svelte';

  const i18n = getContext('i18n');




  interface Props {
    screenCaptureHandler: Function;
    uploadFilesHandler: Function;
    inputFilesHandler: Function;
    uploadGoogleDriveHandler: Function;
    uploadOneDriveHandler: Function;
    selectedToolIds?: string[];
    onClose: Function;
    children?: import('svelte').Snippet;
  }

  let {
    screenCaptureHandler,
    uploadFilesHandler,
    inputFilesHandler,
    uploadGoogleDriveHandler,
    uploadOneDriveHandler,
    selectedToolIds = $bindable([]),
    onClose,
    children
  }: Props = $props();

  let tools = $state({});
  let show = $state(false);


  let fileUploadEnabled = $state(true);

  const init = async () => {
    if ($_tools === null) {
      await _tools.set(await getTools(localStorage.token));
    }

    tools = $_tools.reduce((a, tool, i, arr) => {
      a[tool.id] = {
        name: tool.name,
        description: tool.meta.description,
        enabled: selectedToolIds.includes(tool.id)
      };
      return a;
    }, {});
  };

  const detectMobile = () => {
    const userAgent = navigator.userAgent || navigator.vendor || window.opera;
    return /android|iphone|ipad|ipod|windows phone/i.test(userAgent);
  };

  function handleFileChange(event) {
    const inputFiles = Array.from(event.target?.files);
    if (inputFiles && inputFiles.length > 0) {
      console.log(inputFiles);
      inputFilesHandler(inputFiles);
    }
  }
  run(() => {
    if (show) {
      init();
    }
  });
  run(() => {
    fileUploadEnabled = $user.role === 'admin' || $user?.permissions?.chat?.file_upload;
  });
</script>

<!-- Hidden file input used to open the camera on mobile -->
<input
  id="camera-input"
  style:display="none"
  accept="image/*"
  capture="environment"
  type="file"
  onchange={handleFileChange}
/>

<Dropdown
  bind:show
  on:change={(e) => {
    if (e.detail === false) {
      onClose();
    }
  }}
>
  <Tooltip content={$i18n.t('More')}>
    {@render children?.()}
  </Tooltip>

  {#snippet content()}
    <div >
      <DropdownMenu.Content
        class="w-full max-w-[220px] rounded-xl px-1 py-1  border-gray-300/30 dark:border-gray-700/50 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-sm"
        align="start"
        alignOffset={-8}
        side="top"
        sideOffset={15}
        transition={flyAndScale}
      >
        {#if Object.keys(tools).length > 0}
          <div class="  max-h-28 overflow-y-auto scrollbar-hidden">
            {#each Object.keys(tools) as toolId}
              <button
                class="flex w-full justify-between gap-2 items-center px-3 py-2 text-sm font-medium cursor-pointer rounded-xl"
                onclick={() => {
                tools[toolId].enabled = !tools[toolId].enabled;
              }}
              >
                <div class="flex-1 truncate">
                  <Tooltip
                    className="flex flex-1 gap-2 items-center"
                    content={tools[toolId]?.description ?? ''}
                    placement="top-start"
                  >
                    <div class="shrink-0">
                      <WrenchSolid />
                    </div>

                    <div class=" truncate">{tools[toolId].name}</div>
                  </Tooltip>
                </div>

                <div class=" shrink-0">
                  <Switch
                    state={tools[toolId].enabled}
                    on:change={async (e) => {
                      const state = e.detail;
                      await tick();
                      if (state) {
                        selectedToolIds = [...selectedToolIds, toolId];
                      } else {
                        selectedToolIds = selectedToolIds.filter((id) => id !== toolId);
                      }
                    }}
                  />
                </div>
              </button>
            {/each}
          </div>

          <hr class="border-black/5 dark:border-white/5 my-1" />
        {/if}

        <Tooltip
          className="w-full"
          content={!fileUploadEnabled ? $i18n.t('You do not have permission to upload files') : ''}
        >
          <DropdownMenu.Item
            class="flex gap-2 items-center px-3 py-2 text-sm  font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800  rounded-xl {!fileUploadEnabled
              ? 'opacity-50'
              : ''}"
            on:click={() => {
              if (fileUploadEnabled) {
                if (!detectMobile()) {
                  screenCaptureHandler();
                } else {
                  const cameraInputElement = document.getElementById('camera-input');

                  if (cameraInputElement) {
                    cameraInputElement.click();
                  }
                }
              }
            }}
          >
            <CameraSolid />
            <div class=" line-clamp-1">{$i18n.t('Capture')}</div>
          </DropdownMenu.Item>
        </Tooltip>

        <Tooltip
          className="w-full"
          content={!fileUploadEnabled ? $i18n.t('You do not have permission to upload files') : ''}
        >
          <DropdownMenu.Item
            class="flex gap-2 items-center px-3 py-2 text-sm font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl {!fileUploadEnabled
              ? 'opacity-50'
              : ''}"
            on:click={() => {
              if (fileUploadEnabled) {
                uploadFilesHandler();
              }
            }}
          >
            <DocumentArrowUpSolid />
            <div class="line-clamp-1">{$i18n.t('Upload Files')}</div>
          </DropdownMenu.Item>
        </Tooltip>

        {#if $config?.features?.enable_google_drive_integration}
          <DropdownMenu.Item
            class="flex gap-2 items-center px-3 py-2 text-sm font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
            on:click={() => {
              uploadGoogleDriveHandler();
            }}
          >
            <svg
              class="w-5 h-5"
              viewBox="0 0 87.3 78"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="m6.6 66.85 3.85 6.65c.8 1.4 1.95 2.5 3.3 3.3l13.75-23.8h-27.5c0 1.55.4 3.1 1.2 4.5z"
                fill="#0066da"
              />
              <path
                d="m43.65 25-13.75-23.8c-1.35.8-2.5 1.9-3.3 3.3l-25.4 44a9.06 9.06 0 0 0 -1.2 4.5h27.5z"
                fill="#00ac47"
              />
              <path
                d="m73.55 76.8c1.35-.8 2.5-1.9 3.3-3.3l1.6-2.75 7.65-13.25c.8-1.4 1.2-2.95 1.2-4.5h-27.502l5.852 11.5z"
                fill="#ea4335"
              />
              <path
                d="m43.65 25 13.75-23.8c-1.35-.8-2.9-1.2-4.5-1.2h-18.5c-1.6 0-3.15.45-4.5 1.2z"
                fill="#00832d"
              />
              <path
                d="m59.8 53h-32.3l-13.75 23.8c1.35.8 2.9 1.2 4.5 1.2h50.8c1.6 0 3.15-.45 4.5-1.2z"
                fill="#2684fc"
              />
              <path
                d="m73.4 26.5-12.7-22c-.8-1.4-1.95-2.5-3.3-3.3l-13.75 23.8 16.15 28h27.45c0-1.55-.4-3.1-1.2-4.5z"
                fill="#ffba00"
              />
            </svg>
            <div class="line-clamp-1">{$i18n.t('Google Drive')}</div>
          </DropdownMenu.Item>
        {/if}

        {#if $config?.features?.enable_onedrive_integration}
          <DropdownMenu.Item
            class="flex gap-2 items-center px-3 py-2 text-sm font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
            on:click={() => {
              uploadOneDriveHandler();
            }}
          >
            <svg
              class="w-5 h-5"
              fill="none"
              viewBox="0 0 32 32"
              xmlns="http://www.w3.org/2000/svg"
            >
              <mask
                id="mask0_87_7796"
                style:mask-type="alpha"
                height="20"
                maskUnits="userSpaceOnUse"
                width="32"
                x="0"
                y="6"
              >
                <path
                  d="M7.82979 26C3.50549 26 0 22.5675 0 18.3333C0 14.1921 3.35322 10.8179 7.54613 10.6716C9.27535 7.87166 12.4144 6 16 6C20.6308 6 24.5169 9.12183 25.5829 13.3335C29.1316 13.3603 32 16.1855 32 19.6667C32 23.0527 29 26 25.8723 25.9914L7.82979 26Z"
                  fill="#C4C4C4"
                />
              </mask>
              <g mask="url(#mask0_87_7796)">
                <path
                  d="M7.83017 26.0001C5.37824 26.0001 3.18957 24.8966 1.75391 23.1691L18.0429 16.3335L30.7089 23.4647C29.5926 24.9211 27.9066 26.0001 26.0004 25.9915C23.1254 26.0001 12.0629 26.0001 7.83017 26.0001Z"
                  fill="url(#paint0_linear_87_7796)"
                />
                <path
                  d="M25.5785 13.3149L18.043 16.3334L30.709 23.4647C31.5199 22.4065 32.0004 21.0916 32.0004 19.6669C32.0004 16.1857 29.1321 13.3605 25.5833 13.3337C25.5817 13.3274 25.5801 13.3212 25.5785 13.3149Z"
                  fill="url(#paint1_linear_87_7796)"
                />
                <path
                  d="M7.06445 10.7028L18.0423 16.3333L25.5779 13.3148C24.5051 9.11261 20.6237 6 15.9997 6C12.4141 6 9.27508 7.87166 7.54586 10.6716C7.3841 10.6773 7.22358 10.6877 7.06445 10.7028Z"
                  fill="url(#paint2_linear_87_7796)"
                />
                <path
                  d="M1.7535 23.1687L18.0425 16.3331L7.06471 10.7026C3.09947 11.0792 0 14.3517 0 18.3331C0 20.1665 0.657197 21.8495 1.7535 23.1687Z"
                  fill="url(#paint3_linear_87_7796)"
                />
              </g>
              <defs>
                <linearGradient
                  id="paint0_linear_87_7796"
                  gradientUnits="userSpaceOnUse"
                  x1="4.42591"
                  x2="27.2309"
                  y1="24.6668"
                  y2="23.2764"
                >
                  <stop stop-color="#2086B8" />
                  <stop
                    offset="1"
                    stop-color="#46D3F6"
                  />
                </linearGradient>
                <linearGradient
                  id="paint1_linear_87_7796"
                  gradientUnits="userSpaceOnUse"
                  x1="23.8302"
                  x2="30.2108"
                  y1="19.6668"
                  y2="15.2082"
                >
                  <stop stop-color="#1694DB" />
                  <stop
                    offset="1"
                    stop-color="#62C3FE"
                  />
                </linearGradient>
                <linearGradient
                  id="paint2_linear_87_7796"
                  gradientUnits="userSpaceOnUse"
                  x1="8.51037"
                  x2="23.3335"
                  y1="7.33333"
                  y2="15.9348"
                >
                  <stop stop-color="#0D3D78" />
                  <stop
                    offset="1"
                    stop-color="#063B83"
                  />
                </linearGradient>
                <linearGradient
                  id="paint3_linear_87_7796"
                  gradientUnits="userSpaceOnUse"
                  x1="-0.340429"
                  x2="14.5634"
                  y1="19.9998"
                  y2="14.4649"
                >
                  <stop stop-color="#16589B" />
                  <stop
                    offset="1"
                    stop-color="#1464B7"
                  />
                </linearGradient>
              </defs>
            </svg>
            <div class="line-clamp-1">{$i18n.t('OneDrive')}</div>
          </DropdownMenu.Item>
        {/if}
      </DropdownMenu.Content>
    </div>
  {/snippet}
</Dropdown>
