import csv
import os
import tempfile

import pytest

from open_webui.retrieval.loaders.table import (
    TableAwareCSVLoader,
    TableAwareExcelLoader,
    detect_csv_dialect,
    format_rows_chunk,
)


# ---------------------------------------------------------------------------
# Helper: write a temp CSV with given content
# ---------------------------------------------------------------------------

def _write_csv(content: str, suffix: str = ".csv") -> str:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False, newline="")
    f.write(content)
    f.close()
    return f.name


def _write_bytes(data: bytes, suffix: str = ".csv") -> str:
    f = tempfile.NamedTemporaryFile(mode="wb", suffix=suffix, delete=False)
    f.write(data)
    f.close()
    return f.name


# ---------------------------------------------------------------------------
# detect_csv_dialect
# ---------------------------------------------------------------------------

class TestDetectCsvDialect:
    def test_comma_delimited(self):
        sample = "a,b,c\n1,2,3\n4,5,6\n"
        dialect, has_header = detect_csv_dialect(sample)
        assert dialect.delimiter == ","

    def test_semicolon_delimited(self):
        sample = "a;b;c\n1;2;3\n4;5;6\n"
        dialect, has_header = detect_csv_dialect(sample)
        assert dialect.delimiter == ";"

    def test_tab_delimited(self):
        sample = "a\tb\tc\n1\t2\t3\n4\t5\t6\n"
        dialect, has_header = detect_csv_dialect(sample)
        assert dialect.delimiter == "\t"

    def test_pipe_delimited(self):
        sample = "a|b|c\n1|2|3\n4|5|6\n"
        dialect, has_header = detect_csv_dialect(sample)
        assert dialect.delimiter == "|"

    def test_fallback_on_ambiguous_input(self):
        # Single column, no obvious delimiter -> should not crash
        sample = "hello\nworld\n"
        dialect, has_header = detect_csv_dialect(sample)
        assert dialect is not None


# ---------------------------------------------------------------------------
# format_rows_chunk
# ---------------------------------------------------------------------------

class TestFormatRowsChunk:
    def test_basic_format(self):
        headers = ["Name", "Age"]
        rows = [(0, {"Name": "Alice", "Age": "30"}), (1, {"Name": "Bob", "Age": "25"})]
        result = format_rows_chunk(headers, rows)
        assert "Columns: Name | Age" in result
        assert "Row 0: Alice | 30" in result
        assert "Row 1: Bob | 25" in result

    def test_with_sheet_name(self):
        headers = ["X"]
        rows = [(0, {"X": "1"})]
        result = format_rows_chunk(headers, rows, sheet_name="Sheet1")
        assert result.startswith("Sheet: Sheet1")

    def test_without_sheet_name(self):
        headers = ["X"]
        rows = [(0, {"X": "1"})]
        result = format_rows_chunk(headers, rows)
        assert "Sheet:" not in result


# ---------------------------------------------------------------------------
# TableAwareCSVLoader
# ---------------------------------------------------------------------------

class TestTableAwareCSVLoader:
    def test_basic_csv(self):
        path = _write_csv("name,age,city\nAlice,30,Paris\nBob,25,Lyon\nCharlie,35,Marseille\n")
        try:
            docs = TableAwareCSVLoader(path, rows_per_chunk=2).load()
            assert len(docs) == 2  # 3 rows, chunk size 2 -> 2 chunks
            # First chunk has 2 rows
            assert docs[0].metadata["rows_in_chunk"] == 2
            assert docs[0].metadata["row_range"] == "0-1"
            # Second chunk has 1 row
            assert docs[1].metadata["rows_in_chunk"] == 1
            assert docs[1].metadata["row_range"] == "2-2"
            # Headers in every chunk
            assert "Columns: name | age | city" in docs[0].page_content
            assert "Columns: name | age | city" in docs[1].page_content
            # Row content
            assert "Alice" in docs[0].page_content
            assert "Bob" in docs[0].page_content
            assert "Charlie" in docs[1].page_content
        finally:
            os.unlink(path)

    def test_semicolon_csv(self):
        path = _write_csv("nom;prenom;ville\nDupont;Jean;Paris\nMartin;Marie;Lyon\n")
        try:
            docs = TableAwareCSVLoader(path, rows_per_chunk=5).load()
            assert len(docs) == 1
            assert docs[0].metadata["delimiter"] == ";"
            assert "Dupont" in docs[0].page_content
            assert "Columns: nom | prenom | ville" in docs[0].page_content
        finally:
            os.unlink(path)

    def test_tab_separated(self):
        path = _write_csv("col1\tcol2\n1\t2\n3\t4\n", suffix=".tsv")
        try:
            docs = TableAwareCSVLoader(path, rows_per_chunk=5).load()
            assert len(docs) == 1
            assert docs[0].metadata["delimiter"] == "\t"
        finally:
            os.unlink(path)

    def test_metadata_fields(self):
        path = _write_csv("a,b\n1,2\n")
        try:
            docs = TableAwareCSVLoader(path).load()
            meta = docs[0].metadata
            assert meta["file_type"] == "table"
            assert meta["source"] == path
            assert meta["columns"] == "a, b"
            assert meta["has_header"] is True
        finally:
            os.unlink(path)

    def test_empty_file(self):
        path = _write_csv("")
        try:
            docs = TableAwareCSVLoader(path).load()
            assert docs == []
        finally:
            os.unlink(path)

    def test_whitespace_only_file(self):
        path = _write_csv("   \n  \n")
        try:
            docs = TableAwareCSVLoader(path).load()
            assert docs == []
        finally:
            os.unlink(path)

    def test_single_row(self):
        path = _write_csv("x,y\n10,20\n")
        try:
            docs = TableAwareCSVLoader(path, rows_per_chunk=5).load()
            assert len(docs) == 1
            assert docs[0].metadata["rows_in_chunk"] == 1
        finally:
            os.unlink(path)

    def test_exact_chunk_boundary(self):
        # 4 rows with chunk size 2 -> exactly 2 chunks
        path = _write_csv("a,b\n1,2\n3,4\n5,6\n7,8\n")
        try:
            docs = TableAwareCSVLoader(path, rows_per_chunk=2).load()
            assert len(docs) == 2
            assert docs[0].metadata["rows_in_chunk"] == 2
            assert docs[1].metadata["rows_in_chunk"] == 2
        finally:
            os.unlink(path)

    def test_autodetect_encoding_latin1(self):
        content = "nom,ville\nRéné,Zürich\nÉmile,Genève\n"
        path = _write_bytes(content.encode("latin-1"))
        try:
            docs = TableAwareCSVLoader(path, autodetect_encoding=True).load()
            assert len(docs) == 1
            assert "Réné" in docs[0].page_content
        finally:
            os.unlink(path)

    def test_rows_per_chunk_default(self):
        rows = "h1,h2\n" + "\n".join(f"{i},v{i}" for i in range(12)) + "\n"
        path = _write_csv(rows)
        try:
            docs = TableAwareCSVLoader(path).load()  # default rows_per_chunk=5
            assert len(docs) == 3  # 12 rows / 5 = 3 chunks (5+5+2)
            assert docs[0].metadata["rows_in_chunk"] == 5
            assert docs[2].metadata["rows_in_chunk"] == 2
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# TableAwareExcelLoader
# ---------------------------------------------------------------------------

class TestTableAwareExcelLoader:
    def _write_excel(self, sheets: dict[str, list[dict]], suffix=".xlsx") -> str:
        """Write a multi-sheet Excel file from dict of {sheet_name: [row_dicts]}."""
        path = tempfile.NamedTemporaryFile(suffix=suffix, delete=False).name
        with __import__("pandas").ExcelWriter(path, engine="openpyxl") as writer:
            for sheet_name, rows in sheets.items():
                import pandas as pd
                df = pd.DataFrame(rows)
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        return path

    def test_single_sheet(self):
        path = self._write_excel({
            "Data": [
                {"name": "Alice", "score": "90"},
                {"name": "Bob", "score": "85"},
                {"name": "Charlie", "score": "92"},
            ]
        })
        try:
            docs = TableAwareExcelLoader(path, rows_per_chunk=2).load()
            assert len(docs) == 2
            assert docs[0].metadata["sheet"] == "Data"
            assert docs[0].metadata["file_type"] == "table"
            assert docs[0].metadata["rows_in_chunk"] == 2
            assert docs[1].metadata["rows_in_chunk"] == 1
            assert "Columns: name | score" in docs[0].page_content
            assert "Alice" in docs[0].page_content
            assert "Charlie" in docs[1].page_content
        finally:
            os.unlink(path)

    def test_multi_sheet(self):
        path = self._write_excel({
            "Users": [{"id": "1", "name": "Alice"}],
            "Orders": [{"id": "100", "product": "Widget"}],
        })
        try:
            docs = TableAwareExcelLoader(path, rows_per_chunk=5).load()
            assert len(docs) == 2
            sheets = {d.metadata["sheet"] for d in docs}
            assert sheets == {"Users", "Orders"}
            assert "Sheet: Users" in docs[0].page_content
            assert "Sheet: Orders" in docs[1].page_content
        finally:
            os.unlink(path)

    def test_empty_sheet_skipped(self):
        path = self._write_excel({
            "HasData": [{"a": "1"}],
            "Empty": [],
        })
        try:
            docs = TableAwareExcelLoader(path).load()
            assert len(docs) == 1
            assert docs[0].metadata["sheet"] == "HasData"
        finally:
            os.unlink(path)

    def test_metadata_fields(self):
        path = self._write_excel({
            "Sheet1": [{"x": "10", "y": "20"}],
        })
        try:
            docs = TableAwareExcelLoader(path).load()
            meta = docs[0].metadata
            assert meta["file_type"] == "table"
            assert meta["source"] == path
            assert meta["columns"] == "x, y"
            assert meta["has_header"] is True
            assert meta["row_range"] == "0-0"
        finally:
            os.unlink(path)

    def test_chunking_large_sheet(self):
        import pandas as pd
        rows = [{"col": str(i)} for i in range(13)]
        path = self._write_excel({"Big": rows})
        try:
            docs = TableAwareExcelLoader(path, rows_per_chunk=5).load()
            assert len(docs) == 3  # 13 / 5 = 3 chunks (5+5+3)
            assert docs[0].metadata["rows_in_chunk"] == 5
            assert docs[2].metadata["rows_in_chunk"] == 3
        finally:
            os.unlink(path)

    def test_invalid_file_raises(self):
        path = _write_bytes(b"this is not an excel file", suffix=".xlsx")
        try:
            with pytest.raises(RuntimeError, match="Failed to read Excel file"):
                TableAwareExcelLoader(path).load()
        finally:
            os.unlink(path)
