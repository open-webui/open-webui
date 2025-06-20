<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { onMount } from 'svelte';
  import { generateOpenAIChatCompletion } from '$lib/apis/openai';
  import { models } from '$lib/stores';
  
  export let open = false;
  
  const dispatch = createEventDispatcher();
  
  interface Personal {
    id: string;
    name: string;
    avatar: string;
    prefix: string;
    description?: string;
    createdAt: number;
  }
  
  let personals: Personal[] = [];
  let selectedPersonalId: string | null = null;
  let showCreateForm = false;
  let showEditForm = false;
  let editingPersonal: Personal | null = null;
  
  // 表单数据
  let newPersonal = {
    name: '',
    avatar: '😊',
    description: ''
  };
  
  // 当前生成的前缀
  let currentGeneratedPrefix = 'Hello from !';
  
  // 常用 emoji 供选择
  const commonEmojis = ['😊', '🐱', '🐶', '🦄', '🐼', '🐨', '🦁', '🐯', '🐸', '🐙', '🦋', '🌟', '🌈', '🎈', '🎪', '🎭', '🎨', '🎵', '⚡', '🔥', '💧', '🌙', '☀️', '🌺', '🍀', '🎮', '🚀', '🏰', '👑', '💎', '🎯'];
  
  // 让AI模型生成前缀的函数
  async function generatePrefix(name: string, avatar: string): Promise<string> {
    try {
      // 获取默认模型
      const defaultModel = $models.find(m => m.id) || $models[0];
      if (!defaultModel) {
        return `Hello from ${name}!`;
      }
      
      // 构建提示词让AI生成前缀
      const prompt = `Given a character with name "${name}" and avatar emoji "${avatar}", generate a short, fun, and character-appropriate greeting (2-4 words). This greeting is what the character would say to a child. The greeting should not contain any other names. Return ONLY the greeting itself.`;
      
      // 调用AI API生成前缀
      const response = await generateOpenAIChatCompletion(
        localStorage.token,
        {
          model: defaultModel.id,
          messages: [
            {
              role: 'user',
              content: prompt
            }
          ],
          stream: false,
          max_tokens: 15,
          temperature: 0.7
        }
      );
      
      if (response && response.choices && response.choices[0] && response.choices[0].message) {
        const generatedPrefix = response.choices[0].message.content.trim().replace(/"/g, '');
        return generatedPrefix || `Hello from ${name}!`;
      }
      
      return `Hello from ${name}!`;
    } catch (error) {
      console.error('Error generating prefix:', error);
      return `Hello from ${name}!`;
    }
  }
  
  // 更新前缀预览
  async function updatePrefixPreview() {
    if (newPersonal.name.trim()) {
      currentGeneratedPrefix = await generatePrefix(newPersonal.name.trim(), newPersonal.avatar);
    } else {
      currentGeneratedPrefix = 'Hello from !';
    }
  }
  
  // 响应式更新前缀预览
  $: if (newPersonal.name || newPersonal.avatar) {
    updatePrefixPreview();
  }
  
  function close() {
    open = false;
    showCreateForm = false;
    showEditForm = false;
    editingPersonal = null;
    resetForm();
  }
  
  function resetForm() {
    newPersonal = {
      name: '',
      avatar: '😊',
      description: ''
    };
    currentGeneratedPrefix = 'Hello from !';
  }
  
  function loadPersonals() {
    const saved = localStorage.getItem('personals');
    if (saved) {
      personals = JSON.parse(saved);
    }
    
    const selected = localStorage.getItem('selectedPersonalId');
    if (selected) {
      selectedPersonalId = selected;
    }
  }
  
  function savePersonals() {
    localStorage.setItem('personals', JSON.stringify(personals));
  }
  
  async function createPersonal() {
    if (!newPersonal.name.trim()) {
      alert('Please enter a character name!');
      return;
    }
    
    const generatedPrefix = await generatePrefix(newPersonal.name.trim(), newPersonal.avatar);
    
    const personal: Personal = {
      id: Date.now().toString(),
      name: newPersonal.name.trim(),
      avatar: newPersonal.avatar,
      prefix: generatedPrefix,
      description: newPersonal.description.trim(),
      createdAt: Date.now()
    };
    
    personals = [...personals, personal];
    savePersonals();
    
    // 如果是第一个，自动选择
    if (personals.length === 1) {
      selectPersonal(personal.id);
    }
    
    showCreateForm = false;
    resetForm();
  }
  
  function editPersonal(personal: Personal) {
    editingPersonal = personal;
    newPersonal = {
      name: personal.name,
      avatar: personal.avatar,
      description: personal.description || ''
    };
    showEditForm = true;
  }
  
  async function updatePersonal() {
    if (!editingPersonal || !newPersonal.name.trim()) {
      alert('Please enter a character name!');
      return;
    }
    
    const generatedPrefix = await generatePrefix(newPersonal.name.trim(), newPersonal.avatar);
    
    personals = personals.map(p => 
      p.id === editingPersonal!.id 
        ? {
            ...p,
            name: newPersonal.name.trim(),
            avatar: newPersonal.avatar,
            prefix: generatedPrefix,
            description: newPersonal.description.trim()
          }
        : p
    );
    
    savePersonals();
    showEditForm = false;
    editingPersonal = null;
    resetForm();
  }
  
  function deletePersonal(id: string) {
    if (confirm('Are you sure you want to delete this character?')) {
      personals = personals.filter(p => p.id !== id);
      savePersonals();
      
      // 如果删除的是当前选中的，清空选择
      if (selectedPersonalId === id) {
        selectedPersonalId = null;
        localStorage.removeItem('selectedPersonalId');
        dispatch('personalSelected', null);
      }
    }
  }
  
  function selectPersonal(id: string) {
    selectedPersonalId = id;
    localStorage.setItem('selectedPersonalId', id);
    const personal = personals.find(p => p.id === id);
    dispatch('personalSelected', personal);
    close();
  }
  
  function clearSelection() {
    selectedPersonalId = null;
    localStorage.removeItem('selectedPersonalId');
    dispatch('personalSelected', null);
    close();
  }
  
  onMount(() => {
    loadPersonals();
  });
</script>

{#if open}
  <div class="modal-backdrop" on:click={close}></div>
  <div class="modal">
    <div class="modal-header">
      <h2>🎭 My Character Store</h2>
      <button class="close" on:click={close}>×</button>
    </div>
    
    <div class="modal-body">
      {#if showCreateForm}
        <!-- 创建新角色表单 -->
        <div class="form-section">
          <h3>Create New Character</h3>
          <div class="form-group">
            <label>Character Name:</label>
            <input type="text" bind:value={newPersonal.name} placeholder="e.g., Magic Wizard" />
          </div>
          
          <div class="form-group">
            <label>Choose Avatar:</label>
            <div class="emoji-grid">
              {#each commonEmojis as emoji}
                <button 
                  class="emoji-btn {newPersonal.avatar === emoji ? 'selected' : ''}"
                  on:click={() => newPersonal.avatar = emoji}
                >
                  {emoji}
                </button>
              {/each}
            </div>
          </div>
          
          <div class="form-group">
            <label>Description (Optional):</label>
            <textarea bind:value={newPersonal.description} placeholder="Describe this character..."></textarea>
          </div>
          
          <div class="form-group">
            <label>Auto-generated Prefix:</label>
            <div class="prefix-preview">
              "{currentGeneratedPrefix}"
            </div>
          </div>
          
          <div class="form-actions">
            <button class="btn btn-primary" on:click={createPersonal}>Create Character</button>
            <button class="btn btn-secondary" on:click={() => { showCreateForm = false; resetForm(); }}>Cancel</button>
          </div>
        </div>
        
      {:else if showEditForm}
        <!-- 编辑角色表单 -->
        <div class="form-section">
          <h3>Edit Character</h3>
          <div class="form-group">
            <label>Character Name:</label>
            <input type="text" bind:value={newPersonal.name} placeholder="e.g., Magic Wizard" />
          </div>
          
          <div class="form-group">
            <label>Choose Avatar:</label>
            <div class="emoji-grid">
              {#each commonEmojis as emoji}
                <button 
                  class="emoji-btn {newPersonal.avatar === emoji ? 'selected' : ''}"
                  on:click={() => newPersonal.avatar = emoji}
                >
                  {emoji}
                </button>
              {/each}
            </div>
          </div>
          
          <div class="form-group">
            <label>Description (Optional):</label>
            <textarea bind:value={newPersonal.description} placeholder="Describe this character..."></textarea>
          </div>
          
          <div class="form-group">
            <label>Auto-generated Prefix:</label>
            <div class="prefix-preview">
              "{currentGeneratedPrefix}"
            </div>
          </div>
          
          <div class="form-actions">
            <button class="btn btn-primary" on:click={updatePersonal}>Save Changes</button>
            <button class="btn btn-secondary" on:click={() => { showEditForm = false; editingPersonal = null; resetForm(); }}>Cancel</button>
          </div>
        </div>
        
      {:else}
        <!-- 角色列表 -->
        <div class="store-content">
          <div class="store-header">
            <button class="btn btn-primary" on:click={() => showCreateForm = true}>
              ✨ Create New Character
            </button>
            {#if selectedPersonalId}
              <button class="btn btn-secondary" on:click={clearSelection}>
                🚫 Clear Selection
              </button>
            {/if}
          </div>
          
          {#if personals.length === 0}
            <div class="empty-state">
              <p>🎭 No characters created yet!</p>
              <p>Click "Create New Character" to start your character adventure!</p>
            </div>
          {:else}
            <div class="personals-grid">
              {#each personals as personal}
                <div class="personal-card {selectedPersonalId === personal.id ? 'selected' : ''}">
                  <div class="personal-avatar">{personal.avatar}</div>
                  <div class="personal-info">
                    <h4>{personal.name}</h4>
                    <p class="personal-prefix">"{personal.prefix}"</p>
                    {#if personal.description}
                      <p class="personal-desc">{personal.description}</p>
                    {/if}
                  </div>
                  <div class="personal-actions">
                    {#if selectedPersonalId === personal.id}
                      <span class="selected-badge">✓ Selected</span>
                    {:else}
                      <button class="btn btn-small" on:click={() => selectPersonal(personal.id)}>
                        Select
                      </button>
                    {/if}
                    <button class="btn btn-small btn-edit" on:click={() => editPersonal(personal)}>
                      Edit
                    </button>
                    <button class="btn btn-small btn-delete" on:click={() => deletePersonal(personal.id)}>
                      Delete
                    </button>
                  </div>
                </div>
              {/each}
            </div>
          {/if}
        </div>
      {/if}
    </div>
  </div>
{/if}

<style>
  .modal-backdrop {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.5);
    z-index: 1000;
  }
  
  .modal {
    position: fixed;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    z-index: 1001;
    width: 90vw;
    max-width: 600px;
    max-height: 80vh;
    overflow: hidden;
  }
  
  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 1.5rem;
    border-bottom: 1px solid #eee;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
  }
  
  .modal-header h2 {
    margin: 0;
    font-size: 1.25rem;
  }
  
  .close {
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    color: white;
    padding: 0;
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  .modal-body {
    padding: 1.5rem;
    max-height: 60vh;
    overflow-y: auto;
  }
  
  .store-header {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.5rem;
  }
  
  .btn {
    padding: 0.5rem 1rem;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.9rem;
    transition: all 0.2s;
  }
  
  .btn-primary {
    background: #667eea;
    color: white;
  }
  
  .btn-primary:hover {
    background: #5a6fd8;
  }
  
  .btn-secondary {
    background: #f8f9fa;
    color: #495057;
    border: 1px solid #dee2e6;
  }
  
  .btn-secondary:hover {
    background: #e9ecef;
  }
  
  .btn-small {
    padding: 0.25rem 0.5rem;
    font-size: 0.8rem;
  }
  
  .btn-edit {
    background: #ffc107;
    color: #212529;
  }
  
  .btn-delete {
    background: #dc3545;
    color: white;
  }
  
  .empty-state {
    text-align: center;
    padding: 2rem;
    color: #6c757d;
  }
  
  .personals-grid {
    display: grid;
    gap: 1rem;
  }
  
  .personal-card {
    display: flex;
    align-items: center;
    padding: 1rem;
    border: 2px solid #e9ecef;
    border-radius: 8px;
    transition: all 0.2s;
  }
  
  .personal-card:hover {
    border-color: #667eea;
    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.1);
  }
  
  .personal-card.selected {
    border-color: #667eea;
    background: #f8f9ff;
  }
  
  .personal-avatar {
    font-size: 2rem;
    margin-right: 1rem;
  }
  
  .personal-info {
    flex: 1;
  }
  
  .personal-info h4 {
    margin: 0 0 0.25rem 0;
    font-size: 1.1rem;
  }
  
  .personal-prefix {
    margin: 0 0 0.25rem 0;
    color: #667eea;
    font-weight: 500;
  }
  
  .personal-desc {
    margin: 0;
    font-size: 0.9rem;
    color: #6c757d;
  }
  
  .personal-actions {
    display: flex;
    gap: 0.5rem;
    align-items: center;
  }
  
  .selected-badge {
    background: #28a745;
    color: white;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.8rem;
  }
  
  .form-section {
    max-width: 100%;
  }
  
  .form-section h3 {
    margin: 0 0 1rem 0;
    color: #495057;
  }
  
  .form-group {
    margin-bottom: 1rem;
  }
  
  .form-group label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
    color: #495057;
  }
  
  .form-group input,
  .form-group textarea {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid #ced4da;
    border-radius: 4px;
    font-size: 0.9rem;
  }
  
  .form-group textarea {
    height: 80px;
    resize: vertical;
  }
  
  .prefix-preview {
    padding: 0.5rem;
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 4px;
    color: #667eea;
    font-weight: 500;
    font-style: italic;
  }
  
  .emoji-grid {
    display: grid;
    grid-template-columns: repeat(10, 1fr);
    gap: 0.5rem;
    margin-top: 0.5rem;
  }
  
  .emoji-btn {
    background: none;
    border: 2px solid #e9ecef;
    border-radius: 6px;
    font-size: 1.5rem;
    cursor: pointer;
    padding: 0.5rem;
    transition: all 0.2s;
  }
  
  .emoji-btn:hover {
    border-color: #667eea;
    background: #f8f9ff;
  }
  
  .emoji-btn.selected {
    border-color: #667eea;
    background: #667eea;
    color: white;
  }
  
  .form-actions {
    display: flex;
    gap: 1rem;
    margin-top: 1.5rem;
  }
</style> 