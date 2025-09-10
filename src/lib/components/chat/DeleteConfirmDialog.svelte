<script>
  // Enhanced deletion confirmation with file cleanup info
  export let show = false;
  export let title = "Delete chat?";
  export let fileCount = 0;
  export let imageCount = 0;
</script>

{#if show}
  <div class="modal-overlay">
    <div class="modal-content">
      <h3>{title}</h3>
      <div class="warning-content">
        <p>This action will permanently delete:</p>
        <ul>
          <li>Chat conversation history</li>
          {#if fileCount > 0}
            <li>{fileCount} uploaded file{fileCount > 1 ? 's' : ''}</li>
          {/if}
          {#if imageCount > 0}
            <li>{imageCount} extracted image{imageCount > 1 ? 's' : ''}</li>
          {/if}
        </ul>
        <p><strong>This action cannot be undone.</strong></p>
      </div>
      <!-- Confirmation buttons -->
    </div>
  </div>
{/if}