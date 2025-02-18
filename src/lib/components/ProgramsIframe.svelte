<!-- ProgramsIframe.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { user, settings } from '$lib/stores';
  import i18n from '$lib/i18n';
  
  const REACT_APP_URL = import.meta.env.REACT_APP_URL || '/custom/';
  let iframeElement: HTMLIFrameElement;

  // RTL languages
  const RTL_LANGUAGES = ['ar', 'he', 'fa', 'ur'];

  // Send settings to iframe
  function sendSettingsToIframe() {
    if (iframeElement?.contentWindow) {
      // Get base language code (e.g., 'he' from 'he-IL')
      const langCode = $i18n.language?.split('-')[0] || 'en';
      
      // Determine direction based on language
      const direction = RTL_LANGUAGES.includes(langCode) ? 'RTL' : 'LTR';
      
      console.log('[ProgramsIframe] Sending settings to iframe:', {
        language: langCode,
        chatDirection: direction
      });
      
      const targetOrigin = new URL(REACT_APP_URL).origin;
      iframeElement.contentWindow.postMessage({
        type: 'SETTINGS',
        settings: {
          language: langCode,
          chatDirection: direction
        }
      }, targetOrigin);
    }
  }

  onMount(() => {
    // Handle messages from the iframe
    window.addEventListener('message', (event) => {
      // Get the expected origin from the REACT_APP_URL
      const expectedOrigin = new URL(REACT_APP_URL).origin;
      if (event.origin === expectedOrigin) {
        console.log('[ProgramsIframe] Received message from iframe:', event.data);
        
        // Handle GET_SETTINGS request
        if (event.data.type === 'GET_SETTINGS') {
          console.log('[ProgramsIframe] Received settings request from iframe');
          sendSettingsToIframe();
        }
      }
    });

    // Send initial data to iframe after it loads
    if (iframeElement) {
      iframeElement.onload = () => {
        console.log('[ProgramsIframe] Iframe loaded, sending initial settings');
        sendSettingsToIframe();
      };
    }
  });

  // Watch for settings and language changes
  $: if ($settings || $i18n) {
    const langCode = $i18n.language?.split('-')[0] || 'en';
    console.log('[ProgramsIframe] Settings or language changed:', {
      language: langCode,
      chatDirection: RTL_LANGUAGES.includes(langCode) ? 'RTL' : 'LTR'
    });
    sendSettingsToIframe();
  }
</script>

<div class="w-full h-full bg-white dark:bg-gray-900">
  <iframe
    bind:this={iframeElement}
    src={REACT_APP_URL}
    title="Training Program Designer"
    class="w-full h-full border-0"
    allow="clipboard-read; clipboard-write"
  />
</div> 