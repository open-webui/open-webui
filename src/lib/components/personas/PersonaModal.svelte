<script lang="ts">
  export let open = false;
  function close() { open = false; }
</script>

{#if open}
  <div class="modal-backdrop" on:click={close}></div>
  <div class="modal">
    <div class="modal-header">
      <h2>个人信息 / 个性化</h2>
      <button class="close" on:click={close}>×</button>
    </div>
    <div class="modal-body">
      <p>这里可以展示用户头像、昵称、签名、个性化设置等内容。</p>
      <p>你可以根据需要扩展此内容。</p>
    </div>
  </div>
{/if}

<style>
  .modal-backdrop {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.3);
    z-index: 1000;
  }
  .modal {
    position: fixed;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 2px 16px rgba(0,0,0,0.2);
    z-index: 1001;
    min-width: 320px;
    max-width: 90vw;
  }
  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    border-bottom: 1px solid #eee;
  }
  .modal-body {
    padding: 1rem;
  }
  .close {
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
  }
</style> 