FROM ghcr.io/open-webui/pipelines:main

RUN pip install llama-index llama-index-llms-ollama llama-index-embeddings-ollama llama-index-readers-github

RUN pip install crewai==0.1.24 unstructured==0.10.25 pyowm==3.3.0 tools python-dotenv==1.0.0 langchain_openai==0.0.6

RUN pip install youtube-transcript-api langchain langchain-community langchain-openai langchain-text-splitters langsmith huggingface-hub fastapi chromadb

ADD src/crewai_tools /app/crewai_tools