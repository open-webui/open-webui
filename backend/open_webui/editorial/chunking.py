"""Chunking posicional da Arvore de Blocos (Fatia 4).

Agrupa blocos consecutivos em chunks de ate ~max_chars, SEM quebrar um bloco no
meio, comecando um chunk novo a cada capitulo (heading nivel 1). Cada chunk
guarda a referencia posicional (capitulo, ids dos blocos, intervalo de
caracteres no texto canonico do documento) para reconstrucao/citacao depois.

Sem imports de open_webui.
"""


def _block_text(b: dict) -> str:
    t = b.get("text") or ""
    if not t and b.get("type") == "table":
        rows = (b.get("table") or {}).get("rows") or []
        t = " | ".join(
            c.get("text", "") for r in rows for c in r if c.get("text")
        )
    return t


def chunk_tree(tree: dict, max_chars: int = 2000) -> list:
    blocks = list(tree.get("blocks", []))
    texts = [_block_text(b) for b in blocks]

    # Posicoes no texto canonico do documento ("\n\n".join dos blocos).
    starts = []
    pos = 0
    for i, t in enumerate(texts):
        starts.append(pos)
        pos += len(t) + (2 if i < len(texts) - 1 else 0)
    ends = [starts[i] + len(texts[i]) for i in range(len(texts))]

    chunks = []
    group = []  # indices dos blocos no chunk atual
    cur_len = 0

    def flush():
        if not group:
            return
        first, last = group[0], group[-1]
        text = "\n\n".join(texts[i] for i in group if texts[i])
        chunks.append(
            {
                "chunk_id": "c-%05d" % (len(chunks) + 1),
                "index": len(chunks),
                "chapter_index": blocks[first].get("path", {}).get("chapter_index"),
                "block_ids": [blocks[i]["id"] for i in group],
                "char_start": starts[first],
                "char_end": ends[last],
                "text": text,
            }
        )
        group.clear()

    for i, b in enumerate(blocks):
        is_new_chapter = b.get("type") == "heading" and b.get("level") == 1
        if group and (is_new_chapter or cur_len + len(texts[i]) > max_chars):
            flush()
            cur_len = 0
        group.append(i)
        cur_len += len(texts[i]) + 2

    flush()
    return chunks
