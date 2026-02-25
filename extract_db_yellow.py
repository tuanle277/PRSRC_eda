import re
import csv
from pathlib import Path
from typing import Iterator, Optional, Tuple, List, Union

from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph


# Match "Database Table: Encounter" or "Table: Encounter"; allow leading text/extra spaces.
DB_TABLE_RE = re.compile(
    r"(?:^|\b)(?:Database\s+)?Table\s*[:\-]\s*([^\r\n]+)",
    re.IGNORECASE,
)


def norm_text(s: str) -> str:
    """Normalize text for duplicate detection."""
    s = (s or "").replace("\u00A0", " ")  # nbsp
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_database_table_name(text: str) -> Optional[str]:
    """
    Extract table name from any text containing 'Database Table: ...'.
    Returns the captured name (e.g. 'Encounter') or None.
    """
    m = DB_TABLE_RE.search(text or "")
    if not m:
        return None
    return norm_text(m.group(1))


def iter_block_items_in_order(parent: Union[Document, _Cell]) -> Iterator[Union[Paragraph, Table]]:
    """
    Yield Paragraph and Table objects in document order (top-to-bottom).
    parent: Document (for main body) or _Cell (for content inside a table cell, including nested tables).
    """
    if hasattr(parent, "element") and hasattr(parent.element, "body"):
        parent_elm = parent.element.body
    elif hasattr(parent, "_tc"):
        parent_elm = parent._tc
    else:
        return

    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def iter_blocks_from_story_element(element, doc: Document) -> Iterator[Union[Paragraph, Table]]:
    """
    Yield Paragraph and Table from a story element (e.g. header/footer root).
    element: lxml element whose direct children are block-level (p, tbl).
    """
    for child in element.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, doc)
        elif isinstance(child, CT_Tbl):
            yield Table(child, doc)


def extract_yellow_runs_from_paragraph(p: Paragraph) -> List[str]:
    hits: List[str] = []
    for run in p.runs:
        if run.font.highlight_color == WD_COLOR_INDEX.YELLOW:
            t = norm_text(run.text)
            if t:
                hits.append(t)
    return hits


def extract_dbtable_and_yellow_highlights(
    docx_path: str,
) -> List[Tuple[str, str]]:
    """
    Returns list of (database_table, highlighted_text) in document order.
    Consecutive duplicates (same table + same text) are removed.
    Only the main document body is processed (no headers/footers).
    Nested tables inside cells are processed recursively.
    """
    doc = Document(docx_path)

    current_dbtable: List[str] = [""]  # mutable so nested blocks can update it
    out: List[Tuple[str, str]] = []
    last_pair_norm: Optional[Tuple[str, str]] = None

    def emit(dbtable: str, highlight: str) -> None:
        nonlocal last_pair_norm
        db_n = norm_text(dbtable)
        hi_n = norm_text(highlight)
        if last_pair_norm == (db_n, hi_n):
            return
        out.append((dbtable, highlight))
        last_pair_norm = (db_n, hi_n)

    def process_block(parent: Union[Document, _Cell]) -> None:
        for block in iter_block_items_in_order(parent):
            if isinstance(block, Paragraph):
                new_name = parse_database_table_name(block.text)
                if new_name:
                    current_dbtable[0] = new_name
                for h in extract_yellow_runs_from_paragraph(block):
                    emit(current_dbtable[0], h)
            else:
                # Table: process each cell (includes nested tables)
                for row in block.rows:
                    for cell in row.cells:
                        process_block(cell)

    def process_story_element(element, document: Document) -> None:
        """Process blocks from a story element (header/footer root). Same logic as process_block."""
        for block in iter_blocks_from_story_element(element, document):
            if isinstance(block, Paragraph):
                new_name = parse_database_table_name(block.text)
                if new_name:
                    current_dbtable[0] = new_name
                for h in extract_yellow_runs_from_paragraph(block):
                    emit(current_dbtable[0], h)
            else:
                for row in block.rows:
                    for cell in row.cells:
                        process_block(cell)

    # Main document body
    process_block(doc)

    # Headers and footers (all sections and variants)
    for section in getattr(doc, "sections", []) or []:
        for attr in (
            "header",
            "footer",
            "first_page_header",
            "first_page_footer",
            "even_page_header",
            "even_page_footer",
        ):
            hf = getattr(section, attr, None)
            if hf is None:
                continue
            part = getattr(hf, "_header_part", None) or getattr(hf, "_footer_part", None)
            if part is None:
                continue
            el = getattr(part, "element", None) or getattr(part, "root_element", None)
            if el is not None:
                process_story_element(el, doc)

    return out


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python extract_db_yellow.py /path/to/file.docx")
        raise SystemExit(1)

    docx_path = Path(sys.argv[1])
    if not docx_path.exists():
        raise FileNotFoundError(f"File not found: {docx_path}")

    pairs = extract_dbtable_and_yellow_highlights(str(docx_path))

    out_csv = docx_path.with_suffix("").with_name(docx_path.stem + "_dbtable_yellow.csv")
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["database_table", "highlighted_text"])
        for dbt, text in pairs:
            w.writerow([dbt, text])

    print(f"Extracted {len(pairs)} highlighted items (after consecutive-dedup).")
    print(f"Wrote: {out_csv}")


if __name__ == "__main__":
    main()