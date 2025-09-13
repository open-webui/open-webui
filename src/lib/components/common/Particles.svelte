<script lang="ts">
  import { onMount } from 'svelte';
  import type { Container } from '@tsparticles/engine';
  import { loadFull } from 'tsparticles';

  export let options: any;
  export let url: string | undefined = undefined;

  let particlesContainer: Container | undefined;
  let ParticlesComponent;

  onMount(async () => {
    const { default: Particles } = await import('@tsparticles/svelte');
    const { particlesInit } = await import('@tsparticles/svelte');

    await particlesInit(async (engine) => {
      await loadFull(engine);
    });

    ParticlesComponent = Particles;
  });

  const onParticlesLoaded = (event) => {
    particlesContainer = event.detail.particles;
  };
</script>

{#if ParticlesComponent}
  <svelte:component
    this={ParticlesComponent}
    id="tsparticles"
    class="pointer-events-none absolute top-0 left-0 w-full h-full"
    style="z-index: 4;"
    {options}
    {url}
    on:particlesLoaded={onParticlesLoaded}
  />
{/if}
