"""F2.4 - geracao de texto alternativo (acessibilidade) para imagens.

Percorre os blocos de imagem da Arvore e, para os que NAO tem alt, gera um alt
via uma funcao de visao INJETAVEL `vision(image_bytes, mime) -> str` (sync ou
async). Assim o nucleo e testavel sem chamar IA de verdade. O provedor real de
visao (modelo da plataforma) e passado pelo chamador, onde existe contexto de
modelo/credenciais - NAO aqui.
"""

import base64
import inspect
import logging

log = logging.getLogger(__name__)


async def _maybe_await(value):
    if inspect.isawaitable(value):
        return await value
    return value


async def ensure_alt_text(tree: dict, vision=None) -> dict:
    """Preenche `image.alt` dos blocos de imagem sem alt, usando `vision`.

    Se `vision` for None, nada e gerado (as imagens ficam sem alt) - o provedor
    real e injetado pelo chamador. Nunca sobrescreve um alt ja existente."""
    images = [b for b in tree.get("blocks", []) if b.get("type") == "image"]
    pending = [b for b in images if not (b.get("image") or {}).get("alt")]
    if not pending or vision is None:
        return tree

    for b in pending:
        image = b.get("image") or {}
        b64 = image.get("b64")
        if not b64:
            continue
        try:
            raw = base64.b64decode(b64)
            alt = await _maybe_await(vision(raw, image.get("mime", "image/png")))
        except Exception:
            log.exception("falha ao gerar alt-text de imagem")
            alt = None
        if alt:
            alt = str(alt).strip()
            image["alt"] = alt
            b["image"] = image
            if not b.get("text"):
                b["text"] = alt
    return tree
