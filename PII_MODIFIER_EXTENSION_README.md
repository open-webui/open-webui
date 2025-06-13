# PII Modifier Extension

A modular ProseMirror extension that allows users to hover over text and create modifiers (ignore or mask with custom labels) for the Shield API's PII detection system.

## Features

- **Hover-Based Interaction**: Hover over words (3+ characters) to show modifier popup
- **Custom Label Input**: Text field for entering custom PII labels
- **Smart Context Menus**: Different options for already-detected PII vs. new text
- **Ignore Modifiers**: Mark text to be ignored during PII detection
- **Mask Modifiers**: Force text to be detected as PII with custom labels
- **Shield API Integration**: Export modifiers in Shield API format
- **State Management**: Store modifiers in editor state for PiiDetectionExtension to use
- **Modular Design**: Minimal changes to existing code to prevent merge conflicts

**Note**: This extension does not provide visual highlighting. All visual feedback is handled by the PiiDetectionExtension, which reads the modifiers and applies them during detection.

## Installation & Setup

### 1. Import the Extension

```typescript
import { PiiModifierExtension, addPiiModifierStyles, type PiiModifier } from './RichTextInput/PiiModifierExtension';
```

### 2. Add to RichTextInput Props

```typescript
export let enablePiiModifiers = false;
export let onPiiModifiersChanged: (modifiers: PiiModifier[]) => void = () => {};
export let piiModifierLabels: string[] = [];
```

### 3. Initialize Styles

```typescript
// In onMount function
if (enablePiiModifiers && enablePiiDetection) {
    addPiiModifierStyles();
}
```

### 4. Configure Extension

```typescript
editor = new Editor({
    extensions: [
        // ... other extensions
        ...(enablePiiModifiers && enablePiiDetection
            ? [
                    PiiModifierExtension.configure({
                        enabled: true,
                        onModifiersChanged: onPiiModifiersChanged,
                        availableLabels: piiModifierLabels.length > 0 
                            ? piiModifierLabels 
                            : undefined // Use default labels
                    })
                ]
            : [])
    ]
});
```

## Usage

### Basic Usage

1. **Hover Over Text**: Move your mouse over any word (3+ characters) in the editor
2. **Wait for Popup**: After 300ms, a modifier popup will appear
3. **Choose Action**:
   - **For new text**: Enter a custom label in the text field and click "🎭 Mark as PII"
   - **For already-detected PII**: Click "🚫 Ignore this PII" or enter a new label to override
4. **Interact with Menu**: The popup stays open for 10 seconds or until you interact with it

### Programmatic Usage

```typescript
// Add modifier programmatically
editor.commands.addModifier('ignore', 'John Doe');
editor.commands.addModifier('mask', 'A18.32', 'CASENUMBER');

// Get current modifiers
const modifiers = editor.commands.getModifiers();

// Export for NENNA API
const apiFormat = editor.commands.exportModifiersForApi();

// Clear all modifiers
editor.commands.clearModifiers();
```

## API Integration

### Shield API Format

The extension exports modifiers in the format expected by the Shield API:

```typescript
{
  "text": ["Your text content"],
  "pii_labels": {
    "detect": ["ALL"],
    "ignore": ["EMAIL"]
  },
  "modifiers": [
    { "type": "ignore", "entity": "Dr. Hahn" },
    { "type": "mask", "entity": "A18.32", "label": "CASE" }
  ]
}
```

### Integration with PiiDetectionExtension

The PiiDetectionExtension automatically reads modifiers from the editor state:

```typescript
// The PiiDetectionExtension checks for modifiers when making Shield API calls
// No additional configuration needed - modifiers are automatically included
```

## Configuration Options

### PiiModifierOptions

```typescript
interface PiiModifierOptions {
    enabled: boolean;                           // Enable/disable the extension
    onModifiersChanged?: (modifiers: PiiModifier[]) => void;  // Callback for changes
    availableLabels?: string[];                // Custom PII labels for mask options
}
```

### Custom Labels

Users can enter any custom label in the text field that appears in the hover popup. Labels are automatically converted to uppercase for consistency.

**Common examples:**
- CASE (for case numbers)
- PATIENT_ID
- INVOICE_NUMBER
- CUSTOM_FIELD
- REFERENCE_CODE

The extension does not restrict label choices - users have full flexibility to define their own PII categories.

## Visual Design

### Modifier Popup Only

The PiiModifierExtension only provides the hover popup interface. It does not create any visual highlighting in the editor text.

**Visual elements from this extension:**
- Hover popup with text input and buttons
- Clean design with shadow and rounded corners
- Auto-positioning to stay within screen bounds

**All text highlighting is handled by PiiDetectionExtension:**
- PII detection results (influenced by modifiers)
- Color-coded highlighting based on detection/masking status
- Click-to-toggle functionality for detected PII

### Hover Popup

- Clean, modern design with shadow and rounded corners
- Text input field for custom labels with auto-focus
- Conditional ignore button (only shows for already-detected PII)
- Auto-uppercase label conversion
- Enter key support for quick interaction
- Automatic positioning to stay within screen bounds
- 10-second timeout or interaction-based closing

## Commands

The extension adds several commands to the editor:

### `getModifiers()`
Returns all current modifiers from the editor state.

```typescript
const modifiers = editor.commands.getModifiers();
```

### `clearModifiers()`
Removes all modifiers from the editor state.

```typescript
editor.commands.clearModifiers();
```

### `exportModifiersForApi()`
Exports modifiers in Shield API format.

```typescript
const apiModifiers = editor.commands.exportModifiersForApi();
// Returns: [{ type: "ignore", entity: "Dr. Hahn" }, { type: "mask", entity: "A18.32", label: "CASE" }]
```

## Integration with Existing PII Detection

The modifier extension works seamlessly alongside the existing PiiDetectionExtension:

1. **Modifier Creation**: Users hover over words to create modifier objects
2. **State Storage**: Modifiers are stored in ProseMirror editor state
3. **Detection Integration**: PiiDetectionExtension reads modifiers from state
4. **API Enhancement**: Modifiers are included in Shield API calls to affect detection
5. **Visual Feedback**: PiiDetectionExtension handles all highlighting based on detection results + modifiers

**Key Point**: The PiiModifierExtension only creates modifier objects. The PiiDetectionExtension handles all visual highlighting and API interactions.

### Workflow

```typescript
// 1. User hovers over text → PiiModifierExtension shows popup
// 2. User creates modifier → stored in editor state as modifier object
// 3. PiiDetectionExtension reads modifiers from state  
// 4. Shield API called with text + modifiers
// 5. API returns detection results (influenced by modifiers)
// 6. PiiDetectionExtension applies visual highlighting based on results

// The modifier extension only creates modifier objects
// The detection extension handles all API calls and visual feedback
```

## Interaction Details

### Hover Behavior

- **Hover Delay**: 300ms before popup appears
- **Word Detection**: Only words with 3+ characters trigger popup
- **Boundary Detection**: Uses word boundaries to select complete words
- **Menu Duration**: Popup stays open for 10 seconds or until interaction

### Smart Context Detection

- **New Text**: Shows text input field and "Mark as PII" button
- **Detected PII**: Shows "Ignore this PII" button + text input for relabeling  
- **Words with Existing Modifiers**: No popup shown (modifiers managed through editor state)

## Examples

### Complete Integration Example

```svelte
<script lang="ts">
    import RichTextInput from '$lib/components/common/RichTextInput.svelte';
    import type { PiiModifier } from '$lib/components/common/RichTextInput/PiiModifierExtension';
    
    let piiModifiers: PiiModifier[] = [];
    let editorContent = '';
    let piiApiKey = 'your-shield-api-key';
    
    function handleModifiersChanged(modifiers: PiiModifier[]) {
        piiModifiers = modifiers;
        console.log('Modifiers updated:', modifiers);
        // Modifiers are automatically used by PiiDetectionExtension
    }
</script>

<RichTextInput
    bind:value={editorContent}
    enablePiiDetection={true}
    enablePiiModifiers={true}
    piiApiKey={piiApiKey}
    onPiiModifiersChanged={handleModifiersChanged}
    placeholder="Type your message and hover over words to add modifiers..."
/>

<!-- No manual API calls needed - PiiDetectionExtension handles everything -->
```

### Modular Design Benefits

The PiiModifierExtension is designed to be minimally invasive:

```typescript
// Only 2 new props needed in RichTextInput:
export let enablePiiModifiers = false;
export let onPiiModifiersChanged: (modifiers: PiiModifier[]) => void = () => {};

// Extension only creates modifier objects - no API calls, no highlighting
// PiiDetectionExtension automatically reads modifiers from editor state
// No changes needed to existing PII detection/highlighting logic
// No changes needed to Shield API calling code
// Clean separation of concerns: modifiers vs. detection/display
```

## Troubleshooting

### Common Issues

1. **Hover popup not appearing**: 
   - Ensure `enablePiiModifiers` and `enablePiiDetection` are both true
   - Check that you're hovering over words with 3+ characters
   - Wait for the 300ms hover delay

2. **Styles not applied**: 
   - Verify `addPiiModifierStyles()` is called in `onMount`
   - Check browser console for CSS errors

3. **Modifiers not affecting detection**: 
   - Ensure PiiDetectionExtension is properly reading modifiers from editor state
   - Check that both extensions are enabled in the same editor instance
   - Verify that modifiers are being created (check `onPiiModifiersChanged` callback)

### Debug Mode

Enable console logging by adding debug statements:

```typescript
PiiModifierExtension.configure({
    enabled: true,
    onModifiersChanged: (modifiers) => {
        console.log('PII Modifiers changed:', modifiers);
        onPiiModifiersChanged(modifiers);
    }
})
```

## Browser Support

- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

## Dependencies

- `@tiptap/core`
- `prosemirror-state`
- `prosemirror-view`
- `prosemirror-model`

The extension is designed to work seamlessly with the existing PII detection system and requires minimal additional dependencies. 