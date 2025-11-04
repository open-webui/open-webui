"""Local transformers-based text-to-speech provider."""

from __future__ import annotations

import asyncio
import io
from typing import Any

from open_webui.services.interfaces import TTSService


class LocalTTSService(TTSService):
    def __init__(
        self,
        model: str = "microsoft/speecht5_tts",
        *,
        speaker_dataset: str = "Matthijs/cmu-arctic-xvectors",
        speaker_index: int | None = None,
    ) -> None:
        self._model_name = model
        self._dataset_name = speaker_dataset
        self._speaker_index = speaker_index
        self._pipeline = None
        self._embeddings_dataset = None

    async def synthesize(self, text: str, *, voice: str | None = None, **_: Any) -> bytes:
        return await asyncio.to_thread(self._synthesize_sync, text, voice)

    def _load_resources(self):
        if self._pipeline is None:
            from transformers import pipeline

            self._pipeline = pipeline("text-to-speech", self._model_name)

        if self._embeddings_dataset is None:
            from datasets import load_dataset

            self._embeddings_dataset = load_dataset(self._dataset_name, split="validation")

    def _select_speaker(self, voice: str | None) -> Any:
        embeddings_dataset = self._embeddings_dataset
        if voice and "filename" in embeddings_dataset.features:
            try:
                index = embeddings_dataset["filename"].index(voice)
                return embeddings_dataset[index]["xvector"]
            except ValueError:
                pass

        if self._speaker_index is not None and self._speaker_index < len(embeddings_dataset):
            return embeddings_dataset[self._speaker_index]["xvector"]

        # fallback to the first entry
        return embeddings_dataset[0]["xvector"]

    def _synthesize_sync(self, text: str, voice: str | None) -> bytes:
        import numpy as np
        import soundfile as sf

        self._load_resources()
        speaker_embedding = self._select_speaker(voice)

        synthesis = self._pipeline(
            text,
            forward_params={"speaker_embeddings": np.expand_dims(speaker_embedding, axis=0)},
        )

        buffer = io.BytesIO()
        sf.write(buffer, synthesis["audio"], synthesis["sampling_rate"], format="WAV")
        return buffer.getvalue()

