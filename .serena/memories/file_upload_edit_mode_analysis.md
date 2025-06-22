# File Upload in User Message Edit Mode - Analysis & Implementation Plan

## Current State Analysis

### Frontend Limitations (UserMessage.svelte)

- ✅ Text editing via `editedContent`
- ✅ File removal via `editedFiles.splice(fileIdx, 1)`
- ❌ No file addition mechanism
- ❌ No file replacement capability

### Backend File Upload System

The backend (`/backend/open_webui/routers/files.py`) fully supports:

- ✅ Multi-format support (images, documents, audio, video)
- ✅ Permission checks (`file_upload` permission)
- ✅ File validation (size, extension, content type)
- ✅ Metadata handling (language for STT, etc.)
- ✅ Storage management (local, S3, GCS, Azure)

## Implementation Plan

### Phase 1: Core Functionality

1. Extract file upload utilities to shared location
2. Add InputMenu/Plus button to UserMessage edit mode
3. Implement file addition to `editedFiles`
4. Add hidden file input element

### Key Components to Modify

- **UserMessage.svelte**: Add plus button and file upload UI to edit mode
- **Shared utilities**: Extract file upload functions from MessageInput.svelte
- **Integration**: Reuse existing InputMenu component

### Implementation Approach

- Maintain UI consistency with existing patterns
- Reuse existing file upload infrastructure
- Follow existing permission and validation patterns
- Backward compatible implementation

### Security & Validation

- User permission checks: `$_user?.permissions?.chat?.file_upload`
- File count limits: `$config?.file?.max_count`
- File size limits: `$config?.file?.max_size`
- Extension validation via backend

### UX Flow

1. User clicks Edit → Edit mode activates
2. User clicks Plus button → InputMenu dropdown opens
3. User selects "Upload Files" → File picker opens
4. Files upload → Added to `editedFiles` array
5. User saves → Files included in message update

## Technical Requirements

- Import file upload utilities from MessageInput.svelte
- Add InputMenu component to edit mode
- Handle file state management in `editedFiles`
- Maintain existing file display and removal functionality
