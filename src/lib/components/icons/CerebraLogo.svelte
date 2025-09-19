<script lang="ts">
  import { onMount } from 'svelte';
  
  export let className = 'size-10';
  export let strokeWidth: number | string = 1.9;
  
  let logoSrc = '/static/Logo-light.png';
  
  function updateLogo() {
    const isDarkMode = document.documentElement.classList.contains('dark');
    const isHerMode = document.documentElement.classList.contains('her');
    
    if (isDarkMode || isHerMode) {
      logoSrc = '/static/Logo-dark.png';
    } else {
      logoSrc = '/static/Logo-light.png';
    }
  }
  
  onMount(() => {
    updateLogo();
    
    // Listen for theme changes
    const observer = new MutationObserver(updateLogo);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    });
    
    return () => observer.disconnect();
  });
</script>

<img 
  src={logoSrc} 
  class={className} 
  alt="CerebraUI Logo"
  style="object-fit: contain;"
/>


