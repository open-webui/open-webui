[Our OpenWebUI Location Projects](../)
# Open WebUI Install
<!--Pinecone -->

You can also use our [Docker Setup](docker), but it only provides the backend files for editing.

If you already have an "open-webui" Docker container, the server may already be running at [localhost:3000](http://localhost:3000)


## Make sure you have Ollama installed

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

## Build Locally

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

## Train with a web page

Type # followed by any https:// domain path to ask questions about a specific web page. 
Allow a couple minutes to process each question. You can ask questions about today's headlines:

	#https://yahoo.com

**Digesting the News**
Sample prompt: Create 8 categories that all news stories fall in, and calculate the percentage of stories in each category. The 8 category percentages should add up to 100%. A story can be divided among multiple categories. Then list a sample of three top stories for each of the 5 categories. Include URL links for each article listed using using markdown formatting for each of the 3 articles listed below each of the 8 categories.

<!-- npm run preview didn't have an api. flower -->

[Open WebUI Documentation](https://docs.openwebui.com/)


## To Explore

[Hugging Face Transformers](https://huggingface.co/docs/transformers)
Transformers support framework interoperability between PyTorch, TensorFlow, and JAX

[Location Projects for Open WebUI](../)