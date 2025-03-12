<script lang="ts">
    import { onMount } from 'svelte';
    import { page } from '$app/stores';
  
    const GA_ID = 'G-ZXCJJXH0EF';
  
    onMount(() => {
      if (!window.gtag) {
        const script = document.createElement('script');
        script.async = true;
        script.src = `https://www.googletagmanager.com/gtag/js?id=${GA_ID}`;
        document.head.appendChild(script);
  
        const inlineScript = document.createElement('script');
        inlineScript.innerHTML = `
          window.dataLayer = window.dataLayer || [];
          function gtag(){ dataLayer.push(arguments); }
          gtag('js', new Date());
          gtag('config', '${GA_ID}');
        `;
        document.head.appendChild(inlineScript);
      }
    });
  
    $: {
      if (typeof gtag !== 'undefined') {
        gtag('config', GA_ID, {
          page_title: document.title,
          page_path: $page.url.pathname,
        });
      }
    }
  </script>
  
  <svelte:head>
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-ZXCJJXH0EF"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
  
      function gtag() {
        dataLayer.push(arguments);
      }
  
      gtag('js', new Date());
      gtag('config', 'G-ZXCJJXH0EF');
    </script>
  </svelte:head>
  