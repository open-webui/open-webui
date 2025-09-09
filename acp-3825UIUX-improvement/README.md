## Features implemented

Added support for configurable interactive buttons for SearchPlanAgent responses. The backend reads a JSON configuration from an environment variable and the frontend renders the buttons in the chat UI and handles their actions.

Environment variable
- Name: `SEARCH_PLAN_AGENT_BUTTONS_MAPPING`
- Value: JSON array of button objects

Supported button fields
- `Name` (string) — Button label.
- `OnClickPrependMessageInputText` (string, optional) — Text to prepend to the message input when the button is clicked.
- `OnClickSendMessageAsUserText` (string, optional) — Text sent as if entered by the user when the button is clicked.
- `OnClickDisplayHint` (string, optional) — Hint shown to the user for the button.
- `BackgroundColor` (string, optional) — CSS color for the button background. Get the hex value from https://www.w3schools.com/colors/colors_picker.asp

Example SEARCH_PLAN_AGENT_BUTTONS_MAPPING json
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