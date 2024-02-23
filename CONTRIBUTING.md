# Contribute to Open WebUI

## Project Components

Open WebUI consists of two primary components: the frontend and the backend (which serves as a reverse proxy, handling static frontend files, and additional features). Both need to be running concurrently for the development environment.

> [!IMPORTANT]
> The backend is required for proper functionality

### Requirements 📦

- 🐰 [Bun](https://bun.sh) >= 1.0.21 or 🐢 [Node.js](https://nodejs.org/en) >= 20.10
- 🐍 [Python](https://python.org) >= 3.11

### Build and Install 🛠️

Run the following commands to install:

```sh
git clone https://github.com/open-webui/open-webui.git
cd open-webui/

# Copying required .env file
cp -RPp .env.example .env

# Building Frontend Using Node
npm i
npm run build
# or for development (hot reload)
# npm run dev

# or Building Frontend Using Bun
# bun install
# bun run build

# Serving Frontend with the Backend
cd ./backend
pip install -r requirements.txt -U
sh start.sh
# or for development (hot reload)
# npm run build must have been run once before!
# sh dev.sh
```

You should have Open WebUI up and running at <http://localhost:8080/>. Enjoy! 😄
