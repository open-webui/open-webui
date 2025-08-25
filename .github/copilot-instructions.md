---
applyTo: '**'
---

<!-- # jira task CHAT-866

User's default model does not stick when switching from another chat

Description

When a user creates a new chat, the model from the previous chat is used instead of the default
model. The default model is correctly selected on application start (a hard refresh of the page).

Something I noticed while testing in UAT.

If I set any model as default (e.g. GPT4o), then go to a previous chat that used a different model, then start a new chat, the default model will not load, instead it will remain on the model of the old chat.

To reproduce bug.

Step 1: Select GPT4o as default model.

Step 2: Choose a chat from history that uses different model.

Step 3: Start new chat, default model will not be what was originally selected (GPT4o in my example)

I could not reproduce this bug in Prod, but I could in dev and UAT. -->
