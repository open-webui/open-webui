# PII Detection Loading Indicator Implementation

## Overview
Added a visual loading indicator to the RichTextInput component to show when PII detection API requests are in progress. The indicator appears as a small spinner with text in the top-right corner of the input field, providing clear feedback to users without interfering with text input.

## Implementation Details

### 1. State Management (`PiiDetectionExtension.ts`)
- **Enhanced API Call Tracking**: Modified the `performPiiDetection` function to properly track the `isDetecting` state:
  - Sets `isDetecting: true` when API call starts
  - Sets `isDetecting: false` when API call completes (success or failure)
  - Uses ProseMirror transactions to manage state consistently

- **New Plugin Action**: Added `SET_DETECTING` action type to handle state changes
- **Callback Integration**: Added `onPiiDetectionStateChanged` callback to notify parent components

### 2. UI Component (`RichTextInput.svelte`)
- **Loading State**: Added `isPiiDetectionInProgress` reactive variable
- **Spinner Component**: Integrated the existing `Spinner.svelte` component for consistency
- **Visual Indicator**: Positioned indicator in top-right corner with:
  - Small spinner icon (`size-3`)
  - "Scanning for PII..." text
  - Styled to match application theme (light/dark mode)
  - Non-intrusive overlay design

### 3. Visual Design
The loading indicator features:
- **Position**: Absolute positioning in top-right corner
- **Background**: Themed background with border and shadow
- **Size**: Compact 3-unit spinner with small text
- **Colors**: Matches application's gray color scheme
- **Responsiveness**: Adapts to light/dark mode automatically

## Code Changes

### PiiDetectionExtension.ts
```typescript
// Added to PiiDetectionOptions interface
onPiiDetectionStateChanged?: (isDetecting: boolean) => void;

// In performPiiDetection function
try {
  // Set detecting state to true at the start
  const editorView = this.editor?.view;
  if (editorView) {
    const tr = editorView.state.tr.setMeta(piiDetectionPluginKey, {
      type: 'SET_DETECTING',
      isDetecting: true
    });
    editorView.dispatch(tr);
  }
  
  // ... API call logic ...
  
} finally {
  // Set detecting state to false when done
  const editorView = this.editor?.view;
  if (editorView) {
    const tr = editorView.state.tr.setMeta(piiDetectionPluginKey, {
      type: 'SET_DETECTING',
      isDetecting: false
    });
    editorView.dispatch(tr);
  }
}
```

### RichTextInput.svelte
```svelte
<!-- Loading state variable -->
let isPiiDetectionInProgress = false;

<!-- Callback handler -->
const handlePiiDetectionStateChanged = (isDetecting: boolean) => {
  isPiiDetectionInProgress = isDetecting;
  onPiiDetectionStateChanged(isDetecting);
};

<!-- Visual indicator in template -->
{#if enablePiiDetection && isPiiDetectionInProgress}
  <div class="absolute top-2 right-2 flex items-center gap-1 bg-gray-50 dark:bg-gray-850 px-2 py-1 rounded-md shadow-sm border border-gray-200 dark:border-gray-700">
    <Spinner className="size-3" />
    <span class="text-xs text-gray-600 dark:text-gray-400">Scanning for PII...</span>
  </div>
{/if}
```

## Features

### User Experience
- **Clear Feedback**: Users can see when PII detection is active
- **Non-Intrusive**: Indicator doesn't block text input or interfere with typing
- **Consistent Timing**: Shows for the duration of the debounced API call (500ms delay + API response time)
- **Themed Design**: Matches application's visual style

### Technical Benefits
- **Proper State Management**: Uses ProseMirror's transaction system for consistent state
- **Error Handling**: Indicator clears even if API call fails
- **Performance**: Minimal overhead with reactive state management
- **Maintainability**: Uses existing components and follows established patterns

## Testing

### Manual Testing Steps
1. Enable PII detection in admin settings
2. Configure valid NENNA.ai API key
3. Open a chat window
4. Type text containing PII (e.g., "My name is John Smith")
5. Observe the loading indicator appears in top-right corner
6. Verify indicator disappears when detection completes
7. Test with both light and dark themes
8. Verify indicator shows on API errors and timeouts

### Edge Cases Handled
- API failures (indicator still clears)
- Network timeouts (indicator clears via finally block)
- Rapid typing (debounced to prevent multiple indicators)
- Theme switching (styled for both light/dark modes)
- Empty text (no unnecessary API calls)

## Integration

The loading indicator is automatically enabled when:
- PII detection is enabled (`enablePiiDetection=true`)
- Valid API key is configured
- No additional configuration required in MessageInput component

## Future Enhancements

Potential improvements for future versions:
- Progress bar for long-running detections
- Configurable indicator text/position
- Animation effects for smoother transitions
- Accessibility improvements (ARIA labels, screen reader support)
- Performance metrics display for debugging