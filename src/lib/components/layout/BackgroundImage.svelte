<script lang="ts">
  import { isChatPage } from '$lib/stores';
  import { liveThemeStore } from '$lib/theme';

  let backgroundImageUrl = '';
  let backgroundImageDarken = 0;

  $: {
    const theme = $liveThemeStore;
    let newUrl = '';
    let newDarken = 0;

    if (theme) {
      if ($isChatPage) {
        // We are on a chat page
        if (
          theme.chatBackgroundImageUrl &&
          (theme.toggles?.chatBackgroundImage ?? true)
        ) {
          newUrl = theme.chatBackgroundImageUrl;
          newDarken = theme.chatBackgroundImageDarken ?? 0;
        }
      } else {
        // We are NOT on a chat page
        if (
          theme.systemBackgroundImageUrl &&
          (theme.toggles?.systemBackgroundImage ?? true)
        ) {
          newUrl = theme.systemBackgroundImageUrl;
          newDarken = theme.systemBackgroundImageDarken ?? 0;
        }
      }
    }
    backgroundImageUrl = newUrl;
    backgroundImageDarken = newDarken;
  }
</script>

{#if backgroundImageUrl}
  <div
    class="absolute top-0 left-0 w-full h-full bg-cover bg-center bg-no-repeat"
    style:background-image="url('{backgroundImageUrl}')"
    style:z-index="1"
  ></div>
  <div
    class="absolute top-0 left-0 w-full h-full"
    style:background-color="rgba(0, 0, 0, {backgroundImageDarken / 100})"
    style:z-index="2"
  ></div>
{/if}
