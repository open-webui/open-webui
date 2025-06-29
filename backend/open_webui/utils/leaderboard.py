import numpy as np
from typing import List, Dict
from transformers import AutoTokenizer, AutoModel
import torch

MODEL_NAME = "TaylorAI/bge-micro-v2"
_tokenizer = None
_model = None

def get_tokenizer_and_model():
    global _tokenizer, _model
    if _tokenizer is None or _model is None:
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        _model = AutoModel.from_pretrained(MODEL_NAME)
    return _tokenizer, _model

def get_embedding(text: str) -> np.ndarray:
    tokenizer, model = get_tokenizer_and_model()
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
    embeddings = outputs.last_hidden_state.mean(dim=1).squeeze().cpu().numpy()
    return embeddings

def cosine_similarity(vecA, vecB):
    if np.linalg.norm(vecA) == 0 or np.linalg.norm(vecB) == 0:
        return 0.0
    return float(np.dot(vecA, vecB) / (np.linalg.norm(vecA) * np.linalg.norm(vecB)))

def calculate_model_stats(feedbacks: List[dict], similarities: Dict[str, float]) -> Dict[str, dict]:
    stats = {}
    K = 32

    def get_or_default_stats(model_id):
        return stats.get(model_id, {"rating": 1000, "won": 0, "lost": 0})

    def update_stats(model_id, rating_change, outcome):
        s = get_or_default_stats(model_id)
        s["rating"] += rating_change
        if outcome == 1:
            s["won"] += 1
        elif outcome == 0:
            s["lost"] += 1
        stats[model_id] = s

    def calculate_elo_change(ratingA, ratingB, outcome, similarity):
        expected_score = 1 / (1 + 10 ** ((ratingB - ratingA) / 400))
        return K * (outcome - expected_score) * similarity

    for fb in feedbacks:
        data = fb.get("data", {})
        modelA = data.get("model_id")
        outcome = None
        if str(data.get("rating")) == "1":
            outcome = 1
        elif str(data.get("rating")) == "-1":
            outcome = 0
        else:
            continue
        similarity = similarities.get(fb["id"], 1.0)
        opponents = data.get("sibling_model_ids") or []
        for modelB in opponents:
            statsA = get_or_default_stats(modelA)
            statsB = get_or_default_stats(modelB)
            changeA = calculate_elo_change(statsA["rating"], statsB["rating"], outcome, similarity)
            changeB = calculate_elo_change(statsB["rating"], statsA["rating"], 1 - outcome, similarity)
            update_stats(modelA, changeA, outcome)
            update_stats(modelB, changeB, 1 - outcome)
    return stats

def compute_leaderboard(query: str, feedbacks: List[dict], models: List[dict]) -> List[dict]:
    query_emb = get_embedding(query) if query else None

    tag_emb_cache = {}
    for fb in feedbacks:
        tags = fb.get("data", {}).get("tags", [])
        for tag in tags:
            if tag not in tag_emb_cache:
                tag_emb_cache[tag] = get_embedding(tag)

    similarities = {}
    if query_emb is not None:
        for fb in feedbacks:
            tags = fb.get("data", {}).get("tags", [])
            max_sim = 0.0
            for tag in tags:
                tag_emb = tag_emb_cache.get(tag)
                if tag_emb is not None:
                    sim = cosine_similarity(query_emb, tag_emb)
                    max_sim = max(max_sim, sim)
            similarities[fb["id"]] = max_sim
    else:
        for fb in feedbacks:
            similarities[fb["id"]] = 1.0

    model_stats = calculate_model_stats(feedbacks, similarities)

    leaderboard = []
    for model in models:
        if model.get("owned_by") == "arena" or model.get("info", {}).get("meta", {}).get("hidden", False):
            continue
        stats = model_stats.get(model["id"])
        leaderboard.append({
            "id": model["id"],
            "name": model.get("name", ""),
            "rating": round(stats["rating"]) if stats else "-",
            "stats": {
                "count": (stats["won"] + stats["lost"]) if stats else 0,
                "won": str(stats["won"]) if stats else "-",
                "lost": str(stats["lost"]) if stats else "-"
            },
            "profile_image_url": model.get("info", {}).get("meta", {}).get("profile_image_url", "/favicon.png"),
        })
    leaderboard = sorted(
        leaderboard,
        key=lambda x: (-(x["rating"] if x["rating"] != "-" else -99999), x["name"])
    )
    return leaderboard
