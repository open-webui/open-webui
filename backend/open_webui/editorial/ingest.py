"""Ingestao de documentos editoriais (Fatia 2).

Le o arquivo enviado pelo upload nativo do Open WebUI (file_id -> Files ->
Storage), roda o extrator do formato, guarda a Arvore de Blocos no Storage e
atualiza o registro do documento (status/meta/tree_ref).

Funcao pensada para rodar atras da JobQueue (modo inline na Fatia 1/2; backend
arq na Fatia 2+). Files e Storage sao importados no topo para facilitar o mock
nos testes.
"""

import io
import json
import logging

from open_webui.editorial.extractors import EXTRACTORS, detect_format, get_extractor
from open_webui.models.editorial import Documents
from open_webui.models.files import Files
from open_webui.storage.provider import Storage

log = logging.getLogger(__name__)


async def run_ingestion(document_id: str) -> dict:
    doc = await Documents.get(document_id)
    if doc is None:
        log.warning("ingestao: documento %s nao encontrado", document_id)
        return {"status": "error", "error": "documento nao encontrado"}

    await Documents.set_status(document_id, "parsing")
    try:
        if not doc.file_id:
            raise ValueError("documento sem file_id (nada para ingerir)")

        file_rec = await Files.get_file_by_id(doc.file_id)
        if file_rec is None:
            raise ValueError("arquivo (file_id) nao encontrado no Open WebUI")

        local_path = Storage.get_file(file_rec.path)
        with open(local_path, "rb") as f:
            data = f.read()

        fmt = detect_format(doc.filename or file_rec.filename, doc.format)
        extractor = get_extractor(fmt)
        if extractor is None:
            raise ValueError(
                f"formato nao suportado nesta fase: {fmt!r} "
                f"(suportados: {sorted(EXTRACTORS)})"
            )

        tree = extractor(data)

        tree_bytes = json.dumps(tree, ensure_ascii=False).encode("utf-8")
        tree_name = f"editorial_tree_{document_id}.json"
        _, tree_path = Storage.upload_file(
            io.BytesIO(tree_bytes), tree_name, {"editorial": "tree"}
        )

        blocks = tree.get("blocks", [])
        meta = {
            "title": (tree.get("metadata") or {}).get("title"),
            "format": fmt,
            "blocks": len(blocks),
            "headings": sum(1 for b in blocks if b.get("type") == "heading"),
            "footnotes": sum(1 for b in blocks if b.get("type") == "footnote"),
            "warnings": (tree.get("metadata") or {}).get("warnings", []),
        }
        await Documents.set_result(
            document_id, status="done", meta=meta, tree_ref=tree_path
        )
        return {"status": "done", "tree_ref": tree_path, "meta": meta}

    except Exception as e:
        # Mensagem de erro CLARA fica registrada no proprio documento.
        log.exception("ingestao falhou para %s", document_id)
        await Documents.set_status(document_id, "error", error=str(e))
        return {"status": "error", "error": str(e)}
