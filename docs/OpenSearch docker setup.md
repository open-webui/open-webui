# Setup
- This addresses the setup process between only Open-WebUI and OpenSearch.
- This does not get into the details regarding Ollama, OpenAI, or their models.

## Steps
1. `Docker pull` the images for OpenSearch and Open-WebUI
2. Setup a docker network as these services need to be on the same network to interact with each other correctly. For more info, refer to [Creating a docker network](https://docs.docker.com/reference/cli/docker/network/create/)
3. For the setup process of OpenSearch, refer to [OpenSearch docker setup](https://opensearch.org/docs/latest/install-and-configure/install-opensearch/docker/)
4. To set Open-WebUI to use OpenSearch as the vector database, refer to [Open-WebUI RAG setup](https://docs.openwebui.com/getting-started/env-configuration#retrieval-augmented-generation-rag) and [OpenSearch environment variables](https://docs.openwebui.com/getting-started/env-configuration#opensearch)
5. Ensure that both OpenSearch and Open-WebUI are running within the same docker network by specifying the same in your `docker run` command

## Short note
- While performing the setup process, it is recommended to use OpenSearch with **SSL enabled** as some functionalities will not work on HTTP, but rather on HTTPS, even if not explicitly mentioned.
