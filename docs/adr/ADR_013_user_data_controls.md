# ADR 013: User Data Controls and Privacy Management

> **Status:** Accepted
> **Date:** 2026-01 (commits: a10ac77, 93ed4ae)
> **Deciders:** Open WebUI contributors

## Context

Users need control over their data in Open WebUI:
- **Shared content:** Users share chats via public links but lose track of what's shared
- **Uploaded files:** Users upload documents but can't easily manage them
- **Privacy concerns:** Users want to audit and revoke shared access
- **Compliance:** Some deployments require data governance features

Requirements:
- View all shared chat links
- Revoke sharing on any chat
- View and manage uploaded files
- Bulk operations for cleanup

## Decision

Implement **comprehensive data controls UI** with:

1. **Shared Chats Manager:** View and revoke all shared chat links
2. **Files Manager:** View, download, and delete uploaded files
3. **Centralized settings:** Data controls in user settings panel
4. **Audit capability:** See when items were shared/uploaded

## Consequences

### Positive
- **User empowerment:** Users control their own data
- **Privacy:** Easy to revoke accidental shares
- **Compliance:** Supports data governance requirements
- **Cleanup:** Users can manage storage usage

### Negative
- **UI complexity:** Additional modals and views
- **API surface:** New endpoints for data management
- **Performance:** Listing all files/shares could be slow for heavy users

### Neutral
- Requires user education on new features
- May surface data users forgot about

## Implementation

**Shared Chats Modal:**

```svelte
<!-- components/SharedChatsModal.svelte -->
<script lang="ts">
  import { getSharedChats, unshareChat } from '$lib/apis/chats';

  let sharedChats = [];
  let loading = true;

  onMount(async () => {
    sharedChats = await getSharedChats();
    loading = false;
  });

  async function revoke(chatId: string) {
    await unshareChat(chatId);
    sharedChats = sharedChats.filter(c => c.id !== chatId);
  }
</script>

<Modal title="Shared Chats">
  {#if loading}
    <Loading />
  {:else if sharedChats.length === 0}
    <p>No shared chats</p>
  {:else}
    <table>
      <thead>
        <tr>
          <th>Title</th>
          <th>Shared</th>
          <th>Link</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {#each sharedChats as chat}
          <tr>
            <td>{chat.title}</td>
            <td>{formatDate(chat.shared_at)}</td>
            <td>
              <a href="/s/{chat.share_id}" target="_blank">View</a>
            </td>
            <td>
              <button on:click={() => revoke(chat.id)}>Revoke</button>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  {/if}
</Modal>
```

**Files Modal:**

```svelte
<!-- components/FilesModal.svelte -->
<script lang="ts">
  import { getUserFiles, deleteFile, downloadFile } from '$lib/apis/files';

  let files = [];
  let selectedFiles = new Set();

  async function handleDelete() {
    for (const fileId of selectedFiles) {
      await deleteFile(fileId);
    }
    files = files.filter(f => !selectedFiles.has(f.id));
    selectedFiles.clear();
  }
</script>

<Modal title="My Files">
  <div class="toolbar">
    <button on:click={handleDelete} disabled={selectedFiles.size === 0}>
      Delete Selected ({selectedFiles.size})
    </button>
  </div>

  <table>
    <thead>
      <tr>
        <th><input type="checkbox" on:change={toggleAll} /></th>
        <th>Name</th>
        <th>Size</th>
        <th>Uploaded</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      {#each files as file}
        <tr>
          <td>
            <input
              type="checkbox"
              checked={selectedFiles.has(file.id)}
              on:change={() => toggleFile(file.id)}
            />
          </td>
          <td>{file.filename}</td>
          <td>{formatSize(file.size)}</td>
          <td>{formatDate(file.created_at)}</td>
          <td>
            <button on:click={() => downloadFile(file.id)}>Download</button>
            <button on:click={() => deleteFile(file.id)}>Delete</button>
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
</Modal>
```

**API endpoints:**

```python
# routers/chats.py
@router.get("/shared")
async def get_shared_chats(
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Get all chats shared by the user."""
    return Chats.get_shared_chats_by_user(user.id, db=db)

@router.delete("/{chat_id}/share")
async def unshare_chat(
    chat_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Remove sharing from a chat."""
    chat = Chats.get_chat_by_id(chat_id, db=db)
    if chat.user_id != user.id:
        raise HTTPException(403, "Not authorized")

    chat.share_id = None
    db.commit()
    return {"success": True}

# routers/files.py
@router.get("/user")
async def get_user_files(
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Get all files uploaded by the user."""
    return Files.get_files_by_user(user.id, db=db)

@router.delete("/{file_id}")
async def delete_user_file(
    file_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Delete a file and its storage."""
    file = Files.get_file_by_id(file_id, db=db)
    if file.user_id != user.id:
        raise HTTPException(403, "Not authorized")

    # Delete from storage
    storage.delete(file.path)

    # Delete from vector DB if embedded
    if file.meta.get("embedded"):
        vector_db.delete_by_file_id(file_id)

    # Delete from database
    Files.delete_file(file_id, db=db)

    return {"success": True}
```

**Settings integration:**

```svelte
<!-- routes/(app)/settings/+page.svelte -->
<script>
  import SharedChatsModal from '$lib/components/SharedChatsModal.svelte';
  import FilesModal from '$lib/components/FilesModal.svelte';

  let showSharedChats = false;
  let showFiles = false;
</script>

<section class="data-controls">
  <h2>Data Controls</h2>

  <button on:click={() => showSharedChats = true}>
    Manage Shared Chats
  </button>

  <button on:click={() => showFiles = true}>
    Manage Files
  </button>
</section>

{#if showSharedChats}
  <SharedChatsModal on:close={() => showSharedChats = false} />
{/if}

{#if showFiles}
  <FilesModal on:close={() => showFiles = false} />
{/if}
```

## Data Model Updates

No schema changes required. Uses existing columns:
- `chats.share_id` — Indicates shared status
- `files.user_id` — File ownership

New queries:
- `Chats.get_shared_chats_by_user()` — Filter by `share_id IS NOT NULL`
- `Files.get_files_by_user()` — Already exists

## Alternatives Considered

### Admin-only data management
- Only admins can view/delete user data
- Less user empowerment
- Privacy concerns (admin sees all)
- Rejected for user privacy

### Automatic expiration
- Shared links expire automatically
- Less user control
- May break legitimate use cases
- Considered as future addition

### Data export (GDPR-style)
- Export all user data as ZIP
- Good for compliance
- More complex implementation
- Considered as future addition

## Related Documents

- `DOMAIN_GLOSSARY.md` — Chat, File, Access Control terms
- `DATABASE_SCHEMA.md` — chats, files tables
- `DIRECTIVE_adding_admin_feature.md` — Admin data access patterns

---

*Last updated: 2026-02-03*
