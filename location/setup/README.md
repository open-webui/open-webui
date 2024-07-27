[Our OpenWebUI Location Projects](../)
# Open WebUI Install
<!--Pinecone -->

If you already have an "open-webui" Docker container, your OpenWebUI server may already be running at [localhost:3000](http://localhost:3000) (since Docker restarts it when you start your computer).  You can now [train with a web page](train).

Two options...

### If you are not editing OpenWebUI files

You can use the <a href="https://docs.openwebui.com">Quick Start with Docker (recommended)</a> to install locally. This will automatically include Ollama in your Docker install.


### If you are editing our "projects" fork locally

You can try use our [Docker Setup Experiments](docker) in which we use Docker with a fork of OpenWebUI and extract files to edit in a Webroot. It currently only extracts the backend files for editing.


<div style="border:1px solid #ccc; padding:20px 20px 25px 30px; border-radius:20px;" >

<b>Issue: Storage exceeded when installing Ollama locally</b><br><br>

I had Ollama working fine from the QuickStart above, but since our goal is to build locally, I tried installing Ollama to use with the local build process described below.<br><br>

My install of Ollama locally did not complete due to a storage limitation. I increased the allowed storage, but then my machine was overwhelmed.<br><br>

So now one goal is to install Ollama externally, using the "Different Server" command here: <a href="https://docs.openwebui.com">docs.openwebui.com</a>

</div>

<br>

## Build Locally


### You'll probably need to have Ollama installed

<!--You might need to increase your storage allocation in Docker-->

If Ollama is installed, you should see it here:
[http://localhost:11434](http://localhost:11434)

<!-- Also saw this in Settings > Conections:  http://ollama:11434 -->

**If you don't have Ollama installed yet**
Start with the [Open WebUI Documentation](https://docs.openwebui.com/)

<!--(If you already have an "open-webui" container in Docker, delete or rename it.)-->

<!--
You can run the following in your local projects folder.  

	docker compose up -d --build
-->

<!-- If you already have Ollama running in Docker,
	the above command my exceed the avalable allocated memory. 

Tried again after changind in Docker > Settings > Resources > Advanced
CPU was already at 16
Increased memory limit from 8GB to 24GB
Increase Swap from 1GB to 3GB
-->

Otherwise, here are the steps [if you already have Ollama](https://docs.openwebui.com/)
Or if you're retaining an [existing open-webui container](https://docs.openwebui.com/getting-started/)
<!--
, and using GPU Support, then run:

	docker run -d -p 3000:8080 --gpus=all -v ollama:/root/.ollama -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:ollama
-->

## Run the Build

Open your local build at [localhost:3000](http://localhost:3000)

	npm run build

### More detailed

NOT needed if you are running as a local Docker instance.  

Commands from [Open WebUI Getting Started](https://docs.openwebui.com/getting-started/) for building locally

	python3.11 -m venv env
	source env/bin/activate

	git clone https://github.com/modelearth/projects.git
	cd projects/

<!--
	# Copying required .env file
	cp -RPp .env.example .env
-->

	# Building Frontend Using Node
	npm i
	npm run build


	# Serving Frontend with the Backend
	cd ./backend
	pip install -r requirements.txt -U

	bash start.sh

	npm run dev

## Edit in our Open WebUI "projects/location" folder

The "projects/location" folder is where we'll edit enhancements to the "src" folder.  
We'll merge our enhancments into "src-merged" so we don't have sync issues with open-webui.

We also edit index.html and active.md in our "projects" fork root since we added those files.

<span style="color:red; display:none">
We've temporarily deactivated the following while we move it to another repo. It seems that the large size of the Docker container may have filled our storage space, preventing other pages in the model.earth repos from being deployed. Old pages were stuck in the cache.
</span>

You can either fork and clone our [projects repo](https://github.com/ModelEarth/projects)  
Or you can use our [datascape Docker container image](https://github.com/users/datascape/packages/container/package/projects), which is created from the same modelearth/projects repo.