# Model.earth Open WebUI Projects

## Edit your local files pulled down with Docker

**ghcr.io** stands for GitHub Container Registry, which is a service provided by GitHub for hosting and managing container images.

<!--
Replaced open-webui/open-webui with modelearth/projects
Replaced open-webui-container with projects-container
-->

1. Pull the docker image: docker pull ghcr.io/modelearth/projects:main
2. Create a container: docker create --name projects-container ghcr.io/modelearth/projects:main
3. Run the docker container: docker start projects-container
4. We can cd into the container using: docker exec -it projects-container /bin/bash
5. Copy the files from the container to local. (If you aleady have a projects folder, rename it.)

On a Mac:

		docker cp projects-container:/app/backend "~/Documents/webroot/projects"

On a PC:

		docker cp projects-container:/app/backend "C:/All Files/webroot/projects"


## Contribute to our Open WebUI "projects" repo

Our edits to open-webui reside only in the "projects/locations" folder (plus in index.html and active.md in the root) 

Contributors: Dinesh B, Loren, Yifeng

Currently we're avoiding editing existing files to avoid merge conflicts.
The "location" folder is our area to customize.

TO DO: For Docker installs, document if it's possible to edit our [Projects repo fork of open-webui](https://github.com/modelearth/projects). - Dinesh B

To edit without Docker, you can install using these commands when editing locally (from [Open WebUI Getting Started](https://docs.openwebui.com/getting-started/))

	git clone https://github.com/modelearth/projects.git
	cd projects/

	# Copying required .env file
	cp -RPp .env.example .env

	# Building Frontend Using Node
	npm i
	npm run build

	# Serving Frontend with the Backend
	cd ./backend
	pip install -r requirements.txt -U
	bash start.sh

You should have Open WebUI up and running at http://localhost:8080/.

TO DO: Watch this [Open WebUI video](https://www.youtube.com/watch?v=N-aRJe--txs) and share some cool finding during our meetup.

TO DO: Set up [RAG context](https://docs.openwebui.com/tutorial/rag/) using our [superthermal evaporation](../../evaporation-kits/) page and related articles.

TO DO: Create an example of loading a Python util file that is also loaded by our [RealityStream](../../RealityStream/) app.

TO DO: Include the localsite.js file to add our site header and navigation:

	<link type="text/css" rel="stylesheet" href="https://model.earth/localsite/css/base.css" id="/localsite/css/base.css">

TO DO: Add a script that moves a few pages into the location folder and merges with our customizations.

TO DO: Activate hosting using Cloudflare.

TO DO: Provide a means to upload a list of members from a Google Sheet link.

TO DO: Provide a button for admins to export the list of members as a CSV file.

<!--Pinecone -->
<br>

# Open WebUI Install

If you already have an "open-webui" Docker container, the server may already be running at [localhost:3000](http://localhost:3000)

Start with the [Open WebUI Documentation](https://docs.openwebui.com/)

If you don't have Ollama installed yet, you can run the following in your local projects folder.  
<!--(If you already have an "open-webui" container in Docker, delete or rename it.)-->

	docker compose up -d --build

Otherwise, here are the steps [if you already have Ollama](https://docs.openwebui.com/)
Or if you're retaining an [existing open-webui container](https://docs.openwebui.com/getting-started/)
<!--
, and using GPU Support, then run:

	docker run -d -p 3000:8080 --gpus=all -v ollama:/root/.ollama -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:ollama
-->

Open your local build at [localhost:3000](http://localhost:3000)

	npm run build

### Train with a web page

Type # followed by any https:// domain path to ask questions about a specific web page. 
Allow a couple minutes to process each question. You can ask questions about today's headlines:

	#https://yahoo.com

**Digesting the News (sample request)**
Create 8 categories that all news stories fall in, and calculate the percentage of stories in each category. The 8 category percentages should add up to 100%. A story can be divided among multiple categories. Then list a sample of three top stories for each of the 5 categories. Include URL links for each article listed using using markdown formatting for each of the 3 articles listed below each of the 8 categories.

<!-- npm run preview didn't have an api. flower -->

[Open WebUI Documentation](https://docs.openwebui.com/)