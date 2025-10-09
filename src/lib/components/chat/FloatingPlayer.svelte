<script>
  import { activeTTSAudio } from '$lib/stores/ttsStore.js';

  let isPlaying = false;

  activeTTSAudio.subscribe(audioInstance => {
    if (audioInstance) {
      // Listen to the audio object's events to update the UI
      audioInstance.onplay = () => isPlaying = true;
      audioInstance.onpause = () => isPlaying = false;
    }
  });

  function togglePlayPause() {
    const audio = $activeTTSAudio;
    if (audio) {
      if (isPlaying) {
        audio.pause();
      } else {
        audio.play();
      }
    }
  }

  function stopPlayback() {
    const audio = $activeTTSAudio;
    if (audio) {
      audio.pause();
      activeTTSAudio.set(null); // This will cause the player to disappear
    }
  }
</script>

{#if $activeTTSAudio}
  <div class="floating-player-container">
    <span>Now Playing...</span>
    <button on:click={togglePlayPause}>
      {isPlaying ? 'Pause' : 'Play'}
    </button>
    <button on:click={stopPlayback}>Stop</button>
  </div>
{/if}

<style>
  /* Add CSS to style the player and fix its position to the screen */
  .floating-player-container {
    position: fixed;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    background-color: #333;
    color: white;
    padding: 10px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    gap: 15px;
    z-index: 1000;
  }
</style>