# Project: List of Models

TO DO: Create a web page here in the "list" folder within our [projects](https://github.com/modelearth/projects/) repo to provide a list of Open WebUI's available LLM Models (visible without logging in). When the user logs in, indicate which APIs they have stored in Supabase or their browser's LocalStorage.

Experiment with running .py files in our local instance. You'll find .py and .sh files in the "backend/apps" folder.

1.) Locate the list of default models. You can view the list in the front-end when you install and run locally.

2.) Add javascript or React in the projects/list to displays the model list.

3.) Include an external source of additional models, including country-funded models like Falcon (which was rated better than OpenAI briefly when it was launched fall 2023).

We have sample javascript that could be used to fetch these lists directly from external GitHub repos: https://model.earth/requests/images

4.) Extend the existing means to search these model lists in each app and store API keys using both the existing Supabase process (like in Earthscape Chatbot UI) and in browser LocalStorage.

[API Key Local Storage sample](https://model.earth/localsite/tools/storage/api/)

---

Let's avoid editing pre-existing Open WebUI files directly unless we plan to send a pull request to the [open-webui parent repo](https://github.com/open-webui/open-webui).

Our development could involve reusing some processes from Chatbot UI within Open WebUI. We could pull our [Earthscape](/earthscape/app/) Chatbot UI repo in as a submodule of Open WebUI in our [projects](https://github.com/modelearth/projects/) repo.

When we deploy to a server, we'll use the Open WebUI login process to avoid too much traffic.
