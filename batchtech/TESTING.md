# Trying a BatchTechUI branch next to your current Open WebUI

This uses a **separate data volume and port**, so your current setup and its chats are not touched.
Do not point it at your existing data volume: Open WebUI migrates its database forward on start and cannot always go back.

```bash
git clone https://github.com/bfbatch/batchtech-owebui.git
cd batchtech-owebui
git checkout claude/project-thread-w5t6lw        # the PR branch
docker build -t batchtechui:test .               # takes a while; needs a few GB of disk and RAM
docker run -d --name batchtechui-test -p 3001:8080 \
  --add-host=host.docker.internal:host-gateway \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  -v batchtechui-test-data:/app/backend/data \
  batchtechui:test
```

Open `http://SERVER:3001`, create an admin account (it is a fresh instance), then:

1. The tab, login page and menus say **BatchTechUI**, with the BT logo.
2. Sidebar, above your avatar: the **Server** bar (click it for numbers). GPU shows only if the container can see the GPU
   (add `--gpus all` for NVIDIA, with the NVIDIA container toolkit installed).
3. **Handoffs:** Admin Panel, Settings, turn on sub-agents, and in a model's settings choose which models it may delegate to
   (cloud model delegating to a local one). Ask the cloud model to "use a sub-agent with <local model> to ...".
   A line appears under the reply: "Handing off to <model> (local)", the model's logo spins while it works, then
   "<model> (local) finished in Ns".
4. **Spin:** only the model that is generating spins its logo. Remove the old spin CSS in Theme Designer and paste the
   trimmed file from the project files (branding/theme-designer-css-trimmed.css).

Remove the test: `docker rm -f batchtechui-test && docker volume rm batchtechui-test-data`.
