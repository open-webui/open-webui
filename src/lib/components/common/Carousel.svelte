<script lang="ts">
  import { onMount } from 'svelte';

  export let imageUrls = [
   '/assets/images/adam.jpg',
   '/assets/images/galaxy.jpg',
   '/assets/images/earth.jpg',
   '/assets/images/space.jpg'
  ];
  export let duration = 5000;
  export let showArrows = true;
  let selectedImageIdx = 0;

  onMount(() => {
    if (imageUrls.length > 1) {
      let interval = setInterval(() => {
        nextImage();
      }, duration);

      return () => clearInterval(interval);
    }
  });

  function nextImage() {
    selectedImageIdx = (selectedImageIdx + 1) % imageUrls.length;
  }

  function prevImage() {
    selectedImageIdx = (selectedImageIdx - 1 + imageUrls.length) % imageUrls.length;
  }
</script>

<div class="carousel-container">
  {#each imageUrls as imageUrl, idx (idx)}
   <div
    class="image justify-center absolute top-0 left-0 bg-cover bg-center transition-opacity duration-250"
    style="opacity: {selectedImageIdx === idx ? 1 : 0}; background-image: url('{imageUrl}')"
   ></div>
  {/each}

  {#if showArrows && imageUrls.length > 1}
    <!-- Left button -->
    <button
     class="absolute top-1/2 left-1 transform -translate-y-1/2 text-gray-300 text-3xl p-2"
     on:click={prevImage}
    >
     &#10094;
    </button>

    <!-- Right button -->
    <button
     class="absolute top-1/2 right-1 transform -translate-y-1/2 text-gray-300 text-3xl p-2"
     on:click={nextImage}
    >
     &#10095;
    </button>
  {/if}
</div>

<style>
  .carousel-container {
   width: 100%;
   height: 100%;
  }

  .image {
   position: absolute;
   top: 0;
   left: 0;
   width: 100%;
   height: 100%;
   background-size: cover;
   background-position: center;
   transition: opacity 1s ease-in-out;
   opacity: 0;
  }

  .image:nth-child(1) {
   opacity: 1;
  }
</style>