FROM ollama/ollama:latest

# Keep the model loaded for 24h inside the container
ENV OLLAMA_KEEP_ALIVE=24h \
    MODEL=llama3.2:3b

# Pull the desired model at build time so it is baked into the image layer
RUN ollama pull "$MODEL"

# Expose default Ollama port (the base image already does this, but left for clarity)
EXPOSE 11434

# The base image's default CMD is `serve`, which starts the API
CMD ["serve"] 
