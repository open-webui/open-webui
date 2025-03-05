import os
from sentence_transformers import SentenceTransformer

os.environ["TOKENIZERS_PARALLELISM"] = "false"

source_setence = "배고프다"
sentences = [
    "밥 먹고 싶다.",
    "허기가 느껴진다.",
    "배부르다.",
    "배고프지 않다.",
    "i want to eat",
    "i feel hungry",
    "i am full",
    "i am not hungry",
]

model_names = [
    "sentence-transformers/all-MiniLM-L6-v2",
    "upskyy/bge-m3-korean",
    "jhgan/ko-sroberta-multitask",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
]

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

plt.rc('font', family="NanumGothic")

results = []

for model_name in model_names:
    model = SentenceTransformer(model_name)
    embeddings = model.encode([source_setence] + sentences)
    similarities = model.similarity(embeddings, embeddings)
    results.append([model_name] + similarities[0, 1:].tolist())

df = pd.DataFrame(results, columns=["Model Name"] + sentences)
print(f"Source Sentence: {source_setence}")
print(df)

plt.figure(figsize=(10, 6))
sns.heatmap(df.set_index("Model Name"), annot=True, cmap="coolwarm", cbar=True)
plt.xticks(rotation=15, ha='right')
plt.title(f"유사도: {source_setence}")
plt.savefig("similarity_scores.png")
plt.show()