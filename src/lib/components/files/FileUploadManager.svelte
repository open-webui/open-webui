<script>
  import { onMount } from 'svelte';
  // Assuming a store for user token, e.g., from $app/stores or a custom store
  // For demonstration, let's assume a simple way to get the token.
  // Replace with actual token management from the project.
  // import { token } from '$lib/stores/auth'; // Example, if you have such a store
  let authToken = '';

  onMount(() => {
    // In a real app, you'd get this from a store or secure storage
    authToken = localStorage.getItem('token');
    if (!authToken) {
      console.warn('FileUploadManager: Auth token not found. Uploads will likely fail.');
      // Potentially redirect to login or show an error message
    }
  });

  let selectedFiles = [];
  let feedbackMessages = []; // To store messages like "Uploading...", "Success", "Error"

  function handleFileSelect(event) {
    selectedFiles = Array.from(event.target.files);
    feedbackMessages = selectedFiles.map(file => ({ name: file.name, status: 'pending' }));
  }

  async function uploadFiles() {
    if (selectedFiles.length === 0) {
      feedbackMessages = [{ name: '', status: 'No files selected.' }];
      return;
    }

    if (!authToken) {
      feedbackMessages = [{ name: '', status: 'Authentication token is missing. Cannot upload.' }];
      console.error('Auth token is missing.');
      return;
    }

    feedbackMessages = selectedFiles.map(file => ({ name: file.name, status: 'uploading...' }));

    for (let i = 0; i < selectedFiles.length; i++) {
      const file = selectedFiles[i];
      const formData = new FormData();
      formData.append('file', file);
      // formData.append('metadata', JSON.stringify({ description: 'User uploaded file' })); // Optional metadata

      updateFileStatus(file.name, `Uploading ${file.name}...`);

      try {
        const response = await fetch('/files/', { // Ensure this matches your API base URL if needed
          method: 'POST',
          body: formData,
          headers: {
            'Authorization': `Bearer ${authToken}`,
            // 'Content-Type': 'multipart/form-data' // Fetch API sets this automatically for FormData
          },
        });

        const result = await response.json();

        if (response.ok) {
          updateFileStatus(file.name, `Successfully uploaded ${file.name}. File ID: ${result.id}`);
          console.log('Upload successful:', result);
        } else {
          updateFileStatus(file.name, `Error uploading ${file.name}: ${result.detail || response.statusText}`);
          console.error('Upload failed:', result);
        }
      } catch (error) {
        updateFileStatus(file.name, `Error uploading ${file.name}: ${error.message}`);
        console.error('Upload error:', error);
      }
    }
    // Optionally clear selection after upload attempt
    // selectedFiles = [];
    // document.getElementById('fileInput').value = ''; // Reset file input
  }

  function updateFileStatus(fileName, status) {
    feedbackMessages = feedbackMessages.map(msg =>
      msg.name === fileName ? { ...msg, status } : msg
    );
  }

  function clearSelection() {
    selectedFiles = [];
    feedbackMessages = [];
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
      fileInput.value = ''; // Resets the file input
    }
  }
</script>

<div class="file-upload-manager">
  <h3>Upload Files for RAG</h3>
  <p>Supported types: .pdf, .md, .txt, .png, .jpg, .jpeg</p>

  <input
    type="file"
    id="fileInput"
    multiple
    on:change={handleFileSelect}
    accept=".pdf,.md,.txt,.png,.jpg,.jpeg"
  />

  {#if selectedFiles.length > 0}
    <div class="selected-files">
      <h4>Selected Files:</h4>
      <ul>
        {#each selectedFiles as file}
          <li>{file.name} ({Math.round(file.size / 1024)} KB)</li>
        {/each}
      </ul>
      <button on:click={uploadFiles}>Upload Selected</button>
      <button on:click={clearSelection} class="clear-button">Clear Selection</button>
    </div>
  {/if}

  {#if feedbackMessages.length > 0}
    <div class="feedback-messages">
      <h4>Upload Status:</h4>
      <ul>
        {#each feedbackMessages as message}
          <li class:success={message.status && message.status.toLowerCase().includes('success')}
              class:error={message.status && message.status.toLowerCase().includes('error')}>
            {message.status}
          </li>
        {/each}
      </ul>
    </div>
  {/if}
</div>

<style>
  .file-upload-manager {
    font-family: Arial, sans-serif;
    padding: 20px;
    border: 1px solid #ccc;
    border-radius: 8px;
    max-width: 600px;
    margin: 20px auto;
    background-color: #f9f9f9;
  }

  h3 {
    color: #333;
    text-align: center;
  }

  input[type="file"] {
    display: block;
    margin: 20px auto;
    padding: 10px;
    border: 1px dashed #aaa;
    border-radius: 4px;
    cursor: pointer;
  }

  .selected-files {
    margin-top: 20px;
    padding: 10px;
    background-color: #fff;
    border: 1px solid #eee;
    border-radius: 4px;
  }

  .selected-files h4 {
    margin-top: 0;
    color: #555;
  }

  .selected-files ul {
    list-style-type: none;
    padding: 0;
  }

  .selected-files li {
    padding: 5px 0;
    font-size: 0.9em;
    color: #444;
  }

  button {
    background-color: #007bff;
    color: white;
    border: none;
    padding: 10px 15px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 1em;
    margin-right: 10px;
    transition: background-color 0.2s;
  }

  button:hover {
    background-color: #0056b3;
  }

  .clear-button {
    background-color: #dc3545;
  }
  .clear-button:hover {
    background-color: #c82333;
  }

  .feedback-messages {
    margin-top: 20px;
  }

  .feedback-messages h4 {
    color: #555;
  }

  .feedback-messages ul {
    list-style-type: none;
    padding: 0;
  }

  .feedback-messages li {
    padding: 8px;
    margin-bottom: 5px;
    border-radius: 4px;
    font-size: 0.9em;
  }

  .feedback-messages li.success {
    background-color: #d4edda;
    color: #155724;
    border: 1px solid #c3e6cb;
  }

  .feedback-messages li.error {
    background-color: #f8d7da;
    color: #721c24;
    border: 1px solid #f5c6cb;
  }
</style>
