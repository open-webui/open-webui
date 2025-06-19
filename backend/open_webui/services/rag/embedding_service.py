from sentence_transformers import SentenceTransformer

# Global cache for models to avoid reloading them every time
_model_cache = {}

def get_embeddings(texts: list[str], model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> list[list[float]]:
    if not texts:
        return []

    if model_name not in _model_cache:
        try:
            _model_cache[model_name] = SentenceTransformer(model_name)
        except Exception as e:
            print(f"Error loading SentenceTransformer model {model_name}: {e}")
            # Depending on desired error handling, could raise or return empty list for all texts
            return [[] for _ in texts] # Return empty embeddings for all texts if model fails

    model = _model_cache[model_name]

    try:
        embeddings = model.encode(texts, convert_to_tensor=False) # Returns numpy array
        return [embedding.tolist() for embedding in embeddings] # Convert to list of lists of floats
    except Exception as e:
        print(f"Error generating embeddings with {model_name}: {e}")
        return [[] for _ in texts] # Return empty embeddings if encoding fails
