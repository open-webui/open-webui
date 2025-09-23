## Features implemented

Added support for configurable interactive buttons for SearchPlanAgent responses. The backend reads a JSON configuration from an environment variable and the frontend renders the buttons in the chat UI and handles their actions.

The buttons for search plan agent should only appear, when the following conditions are met: 
1. The last message on a chat is a model response, not a user message. 
2. The model's response contain the text matching environment variable SEARCH_PLAN_AGENT_BUTTONS_TRIGGERING_SENTENCE 
3. Buttons haven't been clicked before (only in current frontend session, storing button clicking state outside of frontend is never considered, and will never be), as clicking on those buttons will make them disappear, to prevent buttons from being able to be clicked more than once. 

## Environment variables

Both environment variables below follow the same structured description to make them easy to compare and configure.

### SEARCH_PLAN_AGENT_BUTTONS_MAPPING
- Type: string (JSON)
- Name: SEARCH_PLAN_AGENT_BUTTONS_MAPPING
- Default: unset / empty (feature disabled)
- Description: JSON array of button objects that define quick-action buttons rendered by the frontend for SearchPlanAgent responses.
- Supported button fields:
    - `Name` (string) — Button label.
    - `OnClickPrependMessageInputText` (string, optional) — Text to prepend to the message input when the button is clicked.
    - `OnClickSendMessageAsUserText` (string, optional) — Text sent as if entered by the user when the button is clicked.
    - `OnClickDisplayHint` (string, optional) — Hint shown to the user for the button.
    - `BackgroundColor` (string, optional) — CSS color for the button background. Get the hex value from https://www.w3schools.com/colors/colors_picker.asp
- Example (assign as an environment variable string):
```json
SEARCH_PLAN_AGENT_BUTTONS_MAPPING='[
        {
                "Name": "Provide Correction",
                "OnClickPrependMessageInputText": "Please revise your search plan, in this direction: ",
                "OnClickDisplayHint": "Please provide a direction on how the current search plan can be updated."
        },
        {
                "Name": "Confirm",
                "OnClickSendMessageAsUserText": "Yes, go ahead.",
                "BackgroundColor": "green"
        },
        {
                "Name": "DoesNothingButton"
        }
]'
```

### SEARCH_PLAN_AGENT_BUTTONS_TRIGGERING_SENTENCE
- Type: string (optional)
- Name: SEARCH_PLAN_AGENT_BUTTONS_TRIGGERING_SENTENCE
- Default: unset / empty (feature disabled)
- Description: When set, the Search Plan Agent shows its quick-action buttons in the UI whenever the model's response contains text matching this value. The value is used as a trigger string to detect when to surface the buttons.
- Usage:
    - Add to your environment (e.g., in your .env file):
        SEARCH_PLAN_AGENT_BUTTONS_TRIGGERING_SENTENCE="Is this understanding correct? Please answer with 'yes' to proceed or provide a correction."
    - If the model's response includes the configured sentence/text, the Search Plan Agent will display the associated buttons.
    - Leave empty or unset to disable automatic button triggering.
- Notes:
    - Matching is using a containment check against the model response (the configured string is searched for in the response). Adjust the exact trigger string to match the phrasing the model is expected to produce.
    - Use this variable together with SEARCH_PLAN_AGENT_BUTTONS_MAPPING to control when and which buttons appear.