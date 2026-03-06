import csv
import io
import logging
from typing import Iterator

import chardet
import pandas as pd
from langchain_core.documents import Document

log = logging.getLogger(__name__)


def detect_csv_dialect(
    sample: str,
) -> tuple[csv.Dialect, bool]:
    """Auto-detect CSV dialect and header presence from a text sample."""
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
    except csv.Error:
        dialect = csv.excel
    try:
        has_header = csv.Sniffer().has_header(sample)
    except csv.Error:
        has_header = True
    return dialect, has_header


def format_rows_chunk(
    headers: list[str],
    rows: list[tuple[int, dict]],
    sheet_name: str = "",
) -> str:
    """Format a group of rows with column headers as context."""
    lines = []
    if sheet_name:
        lines.append(f"Sheet: {sheet_name}")
    lines.append(f"Columns: {' | '.join(headers)}")
    for row_idx, row_data in rows:
        values = [str(row_data.get(h, "")) for h in headers]
        lines.append(f"Row {row_idx}: {' | '.join(values)}")
    return "\n".join(lines)


def _detect_encoding(file_path: str) -> str:
    """Detect file encoding using chardet."""
    with open(file_path, "rb") as f:
        raw = f.read(32768)
    result = chardet.detect(raw)
    return result.get("encoding", "utf-8") or "utf-8"


class TableAwareCSVLoader:
    """Load CSV/TSV files with row integrity preservation.

    Each chunk contains N complete rows with column headers prepended,
    preserving the tabular structure for better RAG retrieval.
    """

    def __init__(
        self,
        file_path: str,
        autodetect_encoding: bool = False,
        rows_per_chunk: int = 1,
    ):
        self.file_path = file_path
        self.autodetect_encoding = autodetect_encoding
        self.rows_per_chunk = rows_per_chunk

    def load(self) -> list[Document]:
        return list(self.lazy_load())

    def lazy_load(self) -> Iterator[Document]:
        encodings_to_try = ["utf-8"]
        if self.autodetect_encoding:
            detected = _detect_encoding(self.file_path)
            if detected.lower().replace("-", "") != "utf8":
                encodings_to_try = [detected, "utf-8", "latin-1"]

        for encoding in encodings_to_try:
            try:
                with open(self.file_path, "r", newline="", encoding=encoding) as f:
                    yield from self._read_file(f)
                return
            except UnicodeDecodeError:
                continue

        raise RuntimeError(
            f"Failed to decode {self.file_path} with encodings: {encodings_to_try}"
        )

    def _read_file(self, csvfile: io.TextIOWrapper) -> Iterator[Document]:
        sample = csvfile.read(8192)
        csvfile.seek(0)

        if not sample.strip():
            return

        dialect, has_header = detect_csv_dialect(sample)

        csvfile.seek(0)

        if has_header:
            reader = csv.DictReader(csvfile, dialect=dialect)
            headers = reader.fieldnames or []
            rows = []
            for i, row in enumerate(reader):
                rows.append((i, row))
        else:
            # Read first line to count columns, then reset
            csvfile.seek(0)
            first_line_reader = csv.reader(csvfile, dialect=dialect)
            first_row = next(first_line_reader, None)
            if first_row is None:
                return
            num_cols = len(first_row)
            headers = [f"Column_{i}" for i in range(num_cols)]

            csvfile.seek(0)
            reader = csv.DictReader(csvfile, fieldnames=headers, dialect=dialect)
            rows = []
            for i, row in enumerate(reader):
                rows.append((i, row))

        if not headers or not rows:
            return

        # Group rows into chunks
        for chunk_start in range(0, len(rows), self.rows_per_chunk):
            chunk_end = min(chunk_start + self.rows_per_chunk, len(rows))
            chunk_rows = rows[chunk_start:chunk_end]

            content = format_rows_chunk(headers, chunk_rows)

            metadata = {
                "source": str(self.file_path),
                "file_type": "table",
                "sheet": "",
                "columns": ", ".join(headers),
                "row_range": f"{chunk_rows[0][0]}-{chunk_rows[-1][0]}",
                "rows_in_chunk": len(chunk_rows),
                "delimiter": dialect.delimiter,
                "has_header": has_header,
            }

            yield Document(page_content=content, metadata=metadata)


class TableAwareExcelLoader:
    """Load Excel files with per-sheet row-based chunking.

    Each sheet is processed independently. Chunks contain N complete rows
    with column headers and sheet name as context.
    """

    def __init__(
        self,
        file_path: str,
        rows_per_chunk: int = 1,
    ):
        self.file_path = file_path
        self.rows_per_chunk = rows_per_chunk

    def load(self) -> list[Document]:
        return list(self.lazy_load())

    def lazy_load(self) -> Iterator[Document]:
        try:
            sheets_dict = pd.read_excel(
                self.file_path,
                sheet_name=None,
                dtype=str,
                keep_default_na=False,
            )
        except Exception as e:
            log.warning(
                f"Failed to read Excel file {self.file_path}: {e}"
            )
            raise RuntimeError(
                f"Failed to read Excel file {self.file_path}"
            ) from e

        for sheet_name, df in sheets_dict.items():
            if df.empty:
                log.debug(f"Skipping empty sheet: {sheet_name}")
                continue

            headers = [str(h) for h in df.columns.tolist()]

            for chunk_start in range(0, len(df), self.rows_per_chunk):
                chunk_end = min(chunk_start + self.rows_per_chunk, len(df))
                chunk_df = df.iloc[chunk_start:chunk_end]

                chunk_rows = []
                for row_idx, (_, row) in enumerate(
                    chunk_df.iterrows(), start=chunk_start
                ):
                    row_data = {h: str(row[h]) for h in headers}
                    chunk_rows.append((row_idx, row_data))

                content = format_rows_chunk(headers, chunk_rows, sheet_name=str(sheet_name))

                metadata = {
                    "source": str(self.file_path),
                    "file_type": "table",
                    "sheet": str(sheet_name),
                    "columns": ", ".join(headers),
                    "row_range": f"{chunk_rows[0][0]}-{chunk_rows[-1][0]}",
                    "rows_in_chunk": len(chunk_rows),
                    "delimiter": "",
                    "has_header": True,
                }

                yield Document(page_content=content, metadata=metadata)
