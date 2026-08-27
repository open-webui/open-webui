"""
open_webui.inference
====================

Façade neutre du moteur d'inférence (Ollama / OpenAI / providers compatibles).

Ce package isole l'implémentation du moteur d'inférence du reste de
l'application. Les couches métier (main, utils, routers) ne doivent dépendre
que de cette façade et jamais du détail d'implémentation d'un provider.

Historique : modules déplacés depuis `open_webui.routers.ollama` et
`open_webui.routers.openai` (qui deviennent de minces coquilles HTTP qui
ré-exportent depuis ici).
"""

from open_webui.inference import ollama, openai

__all__ = ['ollama', 'openai']
