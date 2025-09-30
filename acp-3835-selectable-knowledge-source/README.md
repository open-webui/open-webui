# Selectable Knowledge Source Feature

This document outlines the implementation of the selectable knowledge source feature, which allows users to specify knowledge sources for the model to use during a chat session.

## Feature Overview

The selectable knowledge source feature enables users to guide the model's responses by selecting from a predefined list of knowledge sources. When a user starts a new chat and selects one or more knowledge sources, the initial prompt is modified to instruct the model to prioritize information from those sources.

### How It Works

1.  **Configuration**: A mapping between model IDs and available knowledge sources is defined in the backend configuration.
2.  **User Interface**: When a user selects a model, the UI displays buttons for each knowledge source associated with that model.
3.  **Selection**: The user can click on the knowledge source buttons to select or deselect them.
4.  **Prompt Modification**: When a new chat is initiated with knowledge sources selected, a message is appended to the user's prompt, instructing the model to use the selected sources.

## Implementation Details

### Backend

The feature is configured in `backend/open_webui/config.py` using the `MODEL_ID_TO_KNOWLEDGE_SOURCE_MAPPING` setting. This persistent configuration stores a JSON object that maps model IDs to an array of knowledge source names.

**Example Configuration:**

```python
MODEL_ID_TO_KNOWLEDGE_SOURCE_MAPPING = PersistentConfig(
    "MODEL_ID_TO_KNOWLEDGE_SOURCE_MAPPING",
    "ui.model_id_to_knowledge_source_mapping",
    os.environ.get("MODEL_ID_TO_KNOWLEDGE_SOURCE_MAPPING", "{}"),
)
```

An example value for the `MODEL_ID_TO_KNOWLEDGE_SOURCE_MAPPING` environment variable would be:

```json
{
  "gemma:7b": ["Internal Docs", "Product Specs"],
  "llama3:8b": ["General Knowledge", "User Guides"]
}
```

### Frontend

The frontend implementation is handled by three main Svelte components:

-   **`src/lib/components/chat/MessageInput.svelte`**: This component is responsible for rendering the knowledge source selection buttons. It contains a reactive variable `knowledgeSources` that is populated based on the `model_id_to_knowledge_source_mapping` from the config and the currently selected model. When a user clicks a button, the `selectedKnowledgeSources` array is updated.

-   **`src/lib/components/chat/Chat.svelte`**: This component manages the chat session. In the `submitPrompt` function, it checks if the `selectedKnowledgeSources` array is populated. If it is, and the chat is new, it appends a message to the user's prompt.

    ```javascript
    if (
      (messages.length === 0 || history.currentId === null) &&
      selectedKnowledgeSources.length > 0
    ) {
      userPrompt = `${userPrompt}\n\nI have selected these knowledge source(s): [${selectedKnowledgeSources.join(
        ', '
      )}], please find information relevant to my query in these sources.`;
    }
    ```

-   **`src/lib/components/chat/Placeholder.svelte`**: This component also receives the `selectedKnowledgeSources` prop to ensure that the selection is maintained even when the chat view is in its placeholder state.

## Usage

To use this feature:

1.  Set the `MODEL_ID_TO_KNOWLEDGE_SOURCE_MAPPING` environment variable or update the configuration in the database with the desired model-to-source mappings.
2.  In the UI, select a model that has associated knowledge sources.
3.  Click the buttons for the desired knowledge sources to select them.
4.  Start a new chat. The model will be instructed to use the selected sources.
