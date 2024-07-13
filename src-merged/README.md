
## Edit your local files pulled down with Docker

Once you get the following installed, see our [TO DOs for Open WebUI](../location).

**ghcr.io** stands for GitHub Container Registry, which is a service provided by GitHub for hosting and managing container images.

<!--
Replaced open-webui/open-webui with modelearth/projects
Replaced open-webui-container with projects-container
-->

Here are steps to install [the Docker package](https://github.com/modelearth/projects/pkgs/container/projects) created from our "[projects](https://github.com/modelearth/projects)"  fork of open-webui.

<!--
The main Open WebUI container is at:
[https://github.com/orgs/open-webui/packages?repo_name=open-webui](https://github.com/orgs/open-webui/packages?repo_name=open-webui)

We're not an org, so this was not our URL: 
[https://github.com/orgs/modelearth/packages?repo_name=projects](https://github.com/orgs/modelearth/packages?repo_name=projects)
-->

First [update your Docker, Node, Pip, Python and Conda](../../io/coders/python/)

**Run to pull the "projects" Docker container into your Webroot:**

	docker pull ghcr.io/modelearth/projects:main
	docker create --name projects-container ghcr.io/modelearth/projects:main
	docker start projects-container
	docker exec -it projects-container /bin/bash

The above does the following:
1.) Pull the docker image
2.) Create a container called projects-container
3.) Run the docker container
4.) cd into the container


5.) Copy the files from the container to local. If you aleady have a projects folder in your webroot, rename it.
The ~ in the command works for all machines types. On a PC you'll need to use powershell.

	docker cp projects-container:/app/backend "~/Documents/Webroot/projects"

Docker set-up contributors: Dinesh B, Loren, Yifeng

## Edit our Open WebUI "projects" repo

The "location" folder is where we'll edit enhancements to the "src" folder. We'll merge our enhancments into "src-merged" so we don't have sync issues with open-webui.

We also edit index.html and active.md in the repo root.




## We created a Docker "projects" container on GitHub

Advice on [package setup provided by ChatGPT](https://chatgpt.com/share/2200ae05-4f33-4b1c-a1f9-57be4d18257b)

This only needed to be done once by our site admin.  (You can skip this.)  
Settings > Developer settings > Personal access tokens > Tokens (classic)

Generate new token button and in the note put CR_PAT for Container Registry Personal Access Token.  
Choose write:packages (chooses read:packages) and delete:packages

Run the following command to log in to the GitHub Container Registry using your personal access token (starts with ghp_):

	echo your_personal_access_token | docker login ghcr.io -u your_github_username --password-stdin

Now you can build and push your Docker image:
<!-- the first command took about 10 minutes for the build -->
<!-- http://localhost:3000/ probably works before running since Docker starts on startup. -->

	docker build -t ghcr.io/modelearth/projects:main .
	docker push ghcr.io/modelearth/projects:main

Our container then appeared at: [https://github.com/modelearth/projects/pkgs/container/projects](projects/pkgs/container/projects)

## Build Locally

We did NOT need to run the following to setup our Docker instance.  

To build for our Docker container, we can install using these commands from [Open WebUI Getting Started](https://docs.openwebui.com/getting-started/)

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



<!--Pinecone -->
<br>

# Open WebUI Install

We're installing from our [Gihub "projects" Docker container](https://github.com/modelearth/projects/pkgs/container/projects) instead.

You can probably ignore this, or use it to inform your install from our fork.

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