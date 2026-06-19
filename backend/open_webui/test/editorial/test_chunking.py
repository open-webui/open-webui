"""Testes do chunking posicional (Fatia 4). Puro, sem Redis/DB."""

from open_webui.editorial.chunking import chunk_tree


def _make_tree():
    blocks = []
    oid = 0

    def add(btype, text, level=None, chapter=None):
        nonlocal oid
        oid += 1
        b = {
            "id": "b-%06d" % oid,
            "type": btype,
            "order": oid,
            "text": text,
            "inlines": [{"t": "text", "s": text, "marks": []}],
            "path": {"chapter_index": chapter, "chapter_title": None},
        }
        if level:
            b["level"] = level
        blocks.append(b)

    add("heading", "Cap 1", 1, 1)
    add("paragraph", "a" * 500, None, 1)
    add("paragraph", "b" * 500, None, 1)
    add("heading", "Cap 2", 1, 2)
    add("paragraph", "c" * 3000, None, 2)  # bloco maior que max_chars
    return {"blocks": blocks}, blocks


def test_chunks_cover_all_blocks_in_order_without_loss():
    tree, blocks = _make_tree()
    chunks = chunk_tree(tree, max_chars=2000)
    collected = [bid for c in chunks for bid in c["block_ids"]]
    assert collected == [b["id"] for b in blocks]  # cobre tudo, em ordem, sem duplicar


def test_new_chunk_starts_at_each_chapter():
    tree, blocks = _make_tree()
    by_id = {b["id"]: b for b in blocks}
    chunks = chunk_tree(tree, max_chars=2000)
    cap2_id = next(b["id"] for b in blocks if b.get("text") == "Cap 2")
    # o heading do Cap 2 deve ser o PRIMEIRO bloco de algum chunk
    assert any(c["block_ids"][0] == cap2_id for c in chunks)
    # nenhum chunk cruza capitulos
    for c in chunks:
        chapters = {by_id[bid]["path"]["chapter_index"] for bid in c["block_ids"]}
        assert len(chapters) == 1, "um chunk nao deve cruzar capitulos"
    # char ranges comecando em 0 e nao-decrescentes
    assert chunks[0]["char_start"] == 0
    for prev, nxt in zip(chunks, chunks[1:]):
        assert nxt["char_start"] >= prev["char_start"]


def test_oversized_single_block_becomes_its_own_chunk():
    tree, blocks = _make_tree()
    chunks = chunk_tree(tree, max_chars=2000)
    big_id = next(b["id"] for b in blocks if b["text"].startswith("c"))
    big_chunks = [c for c in chunks if big_id in c["block_ids"]]
    assert len(big_chunks) == 1 and big_chunks[0]["block_ids"] == [big_id]
