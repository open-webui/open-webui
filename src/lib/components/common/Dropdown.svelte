<script lang="ts">
  import { DropdownMenu } from 'bits-ui';
  import { createEventDispatcher } from 'svelte';

  import { flyAndScale } from '$lib/utils/transitions';

  export let show = false;
  export let side = 'bottom';
  export let align = 'start';
  const dispatch = createEventDispatcher();
</script>

<DropdownMenu.Root
  closeFocus={false}
  onOpenChange={(state) => {
    dispatch('change', state);
  }}
  typeahead={false}
  bind:open={show}
>
  <DropdownMenu.Trigger>
    <slot />
  </DropdownMenu.Trigger>

  <slot name="content">
    <DropdownMenu.Content
      class="w-full max-w-[130px] rounded-lg px-1 py-1.5 border border-gray-900 z-50 bg-gray-850 text-white"
      {align}
      {side}
      sideOffset={8}
      transition={flyAndScale}
    >
      <DropdownMenu.Item class="flex items-center px-3 py-2 text-sm  font-medium">
        <div class="flex items-center">Profile</div>
      </DropdownMenu.Item>

      <DropdownMenu.Item class="flex items-center px-3 py-2 text-sm  font-medium">
        <div class="flex items-center">Profile</div>
      </DropdownMenu.Item>

      <DropdownMenu.Item class="flex items-center px-3 py-2 text-sm  font-medium">
        <div class="flex items-center">Profile</div>
      </DropdownMenu.Item>
    </DropdownMenu.Content>
  </slot>
</DropdownMenu.Root>
