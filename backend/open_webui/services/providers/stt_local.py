"""Local Whisper (faster-whisper) speech-to-text service."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Sequence

from open_webui.services.interfaces import STTService


class LocalWhisperSTTService(STTService):
    def __init__(
        self,
        model_size: str,
        *,
        device: str = "cpu",
        compute_type: str = "int8",
        download_root: str | None = None,
        vad_filter: bool = False,
        local_files_only: bool = False,
    ) -> None:
        self._model_name = model_size
        self._device = device
        self._compute_type = compute_type
        self._download_root = download_root
        self._vad_filter = vad_filter
        self._local_files_only = local_files_only
        self._model = None

    async def transcribe(
        self,
        audio: bytes,
        *,
        language: str | None = None,
        **_: object,
    ) -> str:
        return await asyncio.to_thread(self._transcribe_sync, audio, language)

    def _load_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            kwargs = {
                "model_size_or_path": self._model_name,
                "device": self._device,
                "compute_type": self._compute_type,
                "local_files_only": self._local_files_only,
            }
            if self._download_root:
                kwargs["download_root"] = self._download_root
            self._model = WhisperModel(**kwargs)
        return self._model

    def _transcribe_sync(self, audio: bytes, language: str | None) -> str:
        model = self._load_model()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio)
            tmp.flush()
            temp_path = Path(tmp.name)

        try:
            segments, info = model.transcribe(
                str(temp_path),
                beam_size=5,
                vad_filter=self._vad_filter,
                language=language,
            )
            transcript = "".join(segment.text for segment in segments)
            if transcript:
                return transcript.strip()
            return ""
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:  # pragma: no cover - best effort cleanup
                pass

