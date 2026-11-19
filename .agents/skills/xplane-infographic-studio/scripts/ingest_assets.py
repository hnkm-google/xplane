#!/usr/bin/env python3
"""Multi-format source asset ingestion for the XPLANE Infographic Studio.

Scans `assets/` recursively while deterministically excluding `assets/XPLANE/`
(the read-only visual style canon), symlinks escaping `assets/` or entering
`assets/XPLANE/`, hidden dotfiles, and Office lockfiles.
"""

from __future__ import annotations

import argparse
import csv
import email
import email.policy
import io
import json
import os
import re
import shutil
import struct
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any, Iterator

try:
    from PIL import Image
except ImportError:  # pragma: no cover - exercised via monkeypatch & system python
    Image = None  # type: ignore[assignment]

try:
    from pptx import Presentation
except ImportError:  # pragma: no cover
    Presentation = None  # type: ignore[assignment]

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parents[4]
MAX_XML_BYTES = 32 * 1024 * 1024  # 32 MB bounded stream cap per zip member

TEXT_EXTS = {".txt", ".md", ".json", ".html", ".htm"}
CSV_EXTS = {".csv", ".tsv"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
CFB_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def _should_skip_name(name: str) -> bool:
    return name.startswith(".") or name.startswith("~$") or name == "__MACOSX"


def _local_tag(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _markdown_table(rows: list[list[str]]) -> str:
    cleaned = [[cell.replace("\n", " ").replace("|", "\\|").strip() for cell in r] for r in rows]
    cleaned = [r for r in cleaned if any(r)]
    if not cleaned:
        return ""
    width = max(len(r) for r in cleaned)
    padded = [r + [""] * (width - len(r)) for r in cleaned]
    header = "| " + " | ".join(padded[0]) + " |"
    sep = "| " + " | ".join(["---"] * width) + " |"
    body = ["| " + " | ".join(r) + " |" for r in padded[1:]]
    return "\n".join([header, sep, *body])


def _read_zip_xml(zf: zipfile.ZipFile, member: str) -> ET.Element:
    with zf.open(member, "r") as fp:
        data = fp.read(MAX_XML_BYTES + 1)
    if len(data) > MAX_XML_BYTES:
        raise ValueError(f"Zip XML member {member} exceeds {MAX_XML_BYTES} bytes")
    return ET.fromstring(data)


def _walk_docx_blocks(elem: ET.Element, blocks: list[str], counts: dict[str, int]) -> None:
    for child in elem:
        lname = _local_tag(child.tag)
        if lname == "p":
            text = "".join(t.text or "" for t in child.iter() if _local_tag(t.tag) == "t").strip()
            if text:
                blocks.append(text)
                counts["paragraphs"] += 1
        elif lname == "tbl":
            rows: list[list[str]] = []
            for tr in child:
                if _local_tag(tr.tag) != "tr":
                    continue
                row_cells: list[str] = []
                for tc in tr:
                    if _local_tag(tc.tag) != "tc":
                        continue
                    paras = [
                        "".join(t.text or "" for t in p.iter() if _local_tag(t.tag) == "t").strip()
                        for p in tc.iter()
                        if _local_tag(p.tag) == "p"
                    ]
                    row_cells.append(" ".join(p for p in paras if p).strip())
                rows.append(row_cells)
            md = _markdown_table(rows)
            if md:
                blocks.append(md)
                counts["tables"] += 1
        else:
            # Unwrap <w:sdt>, <w:sdtContent>, <w:customXml>, etc. recursively
            _walk_docx_blocks(child, blocks, counts)


def _extract_docx(path: Path) -> tuple[str, dict[str, Any]]:
    blocks: list[str] = []
    counts = {"paragraphs": 0, "tables": 0}
    with zipfile.ZipFile(path, "r") as zf:
        root = _read_zip_xml(zf, "word/document.xml")
        body = next((el for el in root if _local_tag(el.tag) == "body"), root)
        _walk_docx_blocks(body, blocks, counts)
    return "\n\n".join(blocks), counts


def _col_ref_to_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha()).upper()
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return max(idx - 1, 0)


def _extract_xlsx(path: Path) -> tuple[str, dict[str, Any]]:
    sections: list[str] = []
    sheet_names: list[str] = []

    with zipfile.ZipFile(path, "r") as zf:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            sst = _read_zip_xml(zf, "xl/sharedStrings.xml")
            for si in sst:
                if _local_tag(si.tag) == "si":
                    shared_strings.append(
                        "".join(t.text or "" for t in si.iter() if _local_tag(t.tag) == "t")
                    )

        rel_map: dict[str, str] = {}
        if "xl/_rels/workbook.xml.rels" in zf.namelist():
            rels_root = _read_zip_xml(zf, "xl/_rels/workbook.xml.rels")
            for rel in rels_root:
                rid = rel.attrib.get("Id", "")
                target = rel.attrib.get("Target", "").lstrip("/")
                if target and not target.startswith("xl/"):
                    target = f"xl/{target}"
                if rid and target:
                    rel_map[rid] = target

        wb = _read_zip_xml(zf, "xl/workbook.xml")
        sheets_el = next((el for el in wb if _local_tag(el.tag) == "sheets"), None)
        sheets = [el for el in (sheets_el if sheets_el is not None else []) if _local_tag(el.tag) == "sheet"]
        for idx, sheet_el in enumerate(sheets, start=1):
            name = sheet_el.attrib.get("name", f"Sheet{idx}")
            sheet_names.append(name)
            rid = next(
                (v for k, v in sheet_el.attrib.items() if _local_tag(k) == "id"),
                "",
            )
            member = rel_map.get(rid, f"xl/worksheets/sheet{idx}.xml")
            if member not in zf.namelist():
                continue
            ws = _read_zip_xml(zf, member)
            rows_out: list[list[str]] = []
            for row_el in ws.iter():
                if _local_tag(row_el.tag) != "row":
                    continue
                cells_by_col: dict[int, str] = {}
                next_col = 0
                for c_el in row_el:
                    if _local_tag(c_el.tag) != "c":
                        continue
                    ref = c_el.attrib.get("r", "")
                    col_idx = _col_ref_to_index(ref) if ref else next_col
                    next_col = col_idx + 1
                    c_type = c_el.attrib.get("t", "")
                    val = ""
                    if c_type == "inlineStr":
                        val = "".join(t.text or "" for t in c_el.iter() if _local_tag(t.tag) == "t")
                    else:
                        v_el = next((ch for ch in c_el if _local_tag(ch.tag) == "v"), None)
                        raw = (v_el.text or "") if v_el is not None else ""
                        if c_type == "s" and raw.isdigit():
                            s_idx = int(raw)
                            val = shared_strings[s_idx] if 0 <= s_idx < len(shared_strings) else raw
                        else:
                            val = raw
                    cells_by_col[col_idx] = val
                if cells_by_col:
                    max_col = max(cells_by_col)
                    rows_out.append([cells_by_col.get(i, "") for i in range(max_col + 1)])
            md = _markdown_table(rows_out)
            if md:
                sections.append(f"#### Sheet: {name}\n\n{md}")

    return "\n\n".join(sections), {"sheets": sheet_names}


def _iter_pptx_shapes(shapes: Any) -> Iterator[Any]:
    for shape in shapes:
        child_shapes = getattr(shape, "shapes", None)
        if child_shapes is not None:
            yield from _iter_pptx_shapes(child_shapes)
        else:
            yield shape


def _extract_pptx_stdlib_xml(path: Path) -> tuple[str, dict[str, Any]]:
    slides_md: list[str] = []
    with zipfile.ZipFile(path, "r") as zf:
        slide_members = sorted(
            (m for m in zf.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", m)),
            key=lambda m: int(re.search(r"(\d+)\.xml$", m).group(1)),  # type: ignore[union-attr]
        )
        for idx, member in enumerate(slide_members, start=1):
            root = _read_zip_xml(zf, member)
            parts: list[str] = []
            for p_el in root.iter():
                if _local_tag(p_el.tag) == "p":
                    txt = "".join(t.text or "" for t in p_el.iter() if _local_tag(t.tag) == "t").strip()
                    if txt:
                        parts.append(txt)
            notes_member = f"ppt/notesSlides/notesSlide{idx}.xml"
            if notes_member in zf.namelist():
                n_root = _read_zip_xml(zf, notes_member)
                n_txt = " ".join(
                    "".join(t.text or "" for t in p.iter() if _local_tag(t.tag) == "t").strip()
                    for p in n_root.iter()
                    if _local_tag(p.tag) == "p"
                ).strip()
                if n_txt:
                    parts.append(f"*Speaker Notes:* {n_txt}")
            if parts:
                slides_md.append(f"#### Slide {idx}\n\n" + "\n\n".join(parts))
        return "\n\n".join(slides_md), {"slides": len(slide_members)}


def _extract_pptx(path: Path) -> tuple[str, dict[str, Any]]:
    if Presentation is None:
        return _extract_pptx_stdlib_xml(path)
    prs = Presentation(str(path))
    slides_md: list[str] = []
    for idx, slide in enumerate(prs.slides, start=1):
        parts: list[str] = []
        for shape in _iter_pptx_shapes(slide.shapes):
            if getattr(shape, "has_text_frame", False):
                txt = "\n".join(
                    p.text.strip() for p in shape.text_frame.paragraphs if p.text and p.text.strip()
                )
                if txt:
                    parts.append(txt)
            if getattr(shape, "has_table", False):
                rows = [
                    [cell.text.strip() for cell in row.cells]
                    for row in shape.table.rows
                ]
                md = _markdown_table(rows)
                if md:
                    parts.append(md)
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
            notes = slide.notes_slide.notes_text_frame.text.strip()
            if notes:
                parts.append(f"*Speaker Notes:* {notes}")
        if parts:
            slides_md.append(f"#### Slide {idx}\n\n" + "\n\n".join(parts))
    return "\n\n".join(slides_md), {"slides": len(prs.slides)}


def _extract_eml(path: Path) -> tuple[str, dict[str, Any]]:
    msg = email.message_from_bytes(path.read_bytes(), policy=email.policy.default)
    headers = []
    for key in ("Subject", "From", "To", "Cc", "Date"):
        if msg.get(key):
            headers.append(f"- **{key}:** {msg.get(key)}")
    body_part = msg.get_body(preferencelist=("plain", "html"))
    body_text = ""
    if body_part is not None:
        raw_body = body_part.get_content()
        if body_part.get_content_type() == "text/html":
            body_text = re.sub(r"<[^>]+>", " ", str(raw_body))
            body_text = re.sub(r"\s+", " ", body_text).strip()
        else:
            body_text = str(raw_body).strip()
    attachments = [
        part.get_filename()
        for part in msg.iter_attachments()
        if part.get_filename()
    ]
    sections = ["\n".join(headers)]
    if body_text:
        sections.append(body_text)
    if attachments:
        sections.append("Attachments: " + ", ".join(attachments))
    return "\n\n".join(s for s in sections if s), {"attachments": attachments}


def _extract_msg(path: Path) -> tuple[str, dict[str, Any]]:
    """Pure-stdlib MS-CFB (OLE2) reader for Outlook .msg MAPI property streams."""
    data = path.read_bytes()
    if len(data) < 512 or data[:8] != CFB_MAGIC:
        raise ValueError("Not a valid OLE2/CFB .msg file")

    major_ver = struct.unpack_from("<H", data, 26)[0]
    sec_shift, mini_shift = struct.unpack_from("<HH", data, 30)
    sec_size = 1 << sec_shift
    mini_size = 1 << mini_shift
    _, num_fat_secs, first_dir_sec, _, mini_cutoff, first_minifat_sec, num_minifat_secs, first_difat_sec, num_difat_secs = (
        struct.unpack_from("<9I", data, 40)
    )

    def get_sector(sec_id: int) -> bytes:
        offset = (sec_id + 1) * sec_size
        if offset < 0 or offset + sec_size > len(data):
            raise ValueError(f"CFB sector {sec_id} out of bounds")
        return data[offset : offset + sec_size]

    difat = [
        s for s in struct.unpack_from("<109I", data, 76) if s < 0xFFFFFFFA
    ]
    curr_difat = first_difat_sec
    ints_per_sec = sec_size // 4
    for _ in range(num_difat_secs):
        if curr_difat >= 0xFFFFFFFA:
            break
        entries = struct.unpack(f"<{ints_per_sec}I", get_sector(curr_difat))
        difat.extend(s for s in entries[:-1] if s < 0xFFFFFFFA)
        curr_difat = entries[-1]

    fat: list[int] = []
    for fat_sec in difat[:num_fat_secs]:
        fat.extend(struct.unpack(f"<{ints_per_sec}I", get_sector(fat_sec)))

    def read_fat_chain(start_sec: int, byte_len: int | None = None) -> bytes:
        chunks: list[bytes] = []
        seen: set[int] = set()
        curr = start_sec
        while curr < 0xFFFFFFFA:
            if curr in seen or curr >= len(fat):
                break
            seen.add(curr)
            chunks.append(get_sector(curr))
            curr = fat[curr]
        raw = b"".join(chunks)
        return raw[:byte_len] if byte_len is not None else raw

    dir_raw = read_fat_chain(first_dir_sec)
    minifat_raw = read_fat_chain(first_minifat_sec) if num_minifat_secs > 0 and first_minifat_sec < 0xFFFFFFFA else b""
    minifat = list(struct.unpack(f"<{len(minifat_raw) // 4}I", minifat_raw)) if minifat_raw else []

    dir_entries: list[tuple[str, int, int, int]] = []
    for pos in range(0, len(dir_raw), 128):
        entry = dir_raw[pos : pos + 128]
        if len(entry) < 128:
            break
        name_cb = struct.unpack_from("<H", entry, 64)[0]
        obj_type = entry[66]
        if obj_type == 0 or name_cb < 2:
            continue
        name = entry[: min(64, name_cb - 2)].decode("utf-16-le", errors="ignore")
        start_sec = struct.unpack_from("<I", entry, 116)[0]
        size = (
            struct.unpack_from("<Q", entry, 120)[0]
            if major_ver == 4
            else struct.unpack_from("<I", entry, 120)[0]
        )
        dir_entries.append((name, obj_type, start_sec, size))

    mini_stream = b""
    for name, obj_type, start_sec, size in dir_entries:
        if obj_type == 5:  # Root Entry owns the MiniStream
            mini_stream = read_fat_chain(start_sec, size)
            break

    def read_mini_chain(start_mini: int, byte_len: int) -> bytes:
        chunks: list[bytes] = []
        seen: set[int] = set()
        curr = start_mini
        while curr < 0xFFFFFFFA:
            if curr in seen:
                break
            seen.add(curr)
            off = curr * mini_size
            chunks.append(mini_stream[off : off + mini_size])
            curr = minifat[curr] if curr < len(minifat) else 0xFFFFFFFE
        return b"".join(chunks)[:byte_len]

    props: dict[str, str] = {}
    attachments: list[str] = []
    html_fallback = ""
    for name, obj_type, start_sec, size in dir_entries:
        if obj_type != 2 or not name.startswith("__substg1.0_") or len(name) < 20 or size == 0:
            continue
        prop_tag = name[12:16].upper()
        prop_type = name[16:20].upper()
        if prop_type not in {"001F", "001E", "0102"}:
            continue
        stream_bytes = (
            read_mini_chain(start_sec, size)
            if size < mini_cutoff and mini_stream
            else read_fat_chain(start_sec, size)
        )
        if prop_type == "001F":
            decoded = stream_bytes.decode("utf-16-le", errors="replace").rstrip("\x00").strip()
        elif prop_type == "001E":
            decoded = stream_bytes.decode("cp1252", errors="replace").rstrip("\x00").strip()
        else:
            decoded = stream_bytes.decode("utf-8", errors="replace").rstrip("\x00").strip()

        if prop_tag in {"3707", "3704"} and decoded and decoded not in attachments:
            attachments.append(decoded)
        elif prop_tag == "1013" and decoded and not html_fallback:
            html_fallback = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", decoded)).strip()
        elif prop_tag not in props and decoded:
            props[prop_tag] = decoded

    headers = []
    subject = props.get("0037", "")
    sender = props.get("0C1A") or props.get("0C1F") or props.get("0065") or ""
    to_val = props.get("0E04", "")
    cc_val = props.get("0E03", "")
    if subject:
        headers.append(f"- **Subject:** {subject}")
    if sender:
        headers.append(f"- **From:** {sender}")
    if to_val:
        headers.append(f"- **To:** {to_val}")
    if cc_val:
        headers.append(f"- **Cc:** {cc_val}")

    body_text = props.get("1000") or html_fallback
    sections = ["\n".join(headers)]
    if body_text:
        sections.append(body_text)
    if attachments:
        sections.append("Attachments: " + ", ".join(attachments))
    return "\n\n".join(s for s in sections if s), {"attachments": attachments}


def _image_dimensions(path: Path) -> tuple[int, int]:
    if Image is not None:
        with Image.open(path) as img:
            return img.size
    proc = subprocess.run(
        ["/usr/bin/sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path.resolve())],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    w_match = re.search(r"pixelWidth:\s*(\d+)", proc.stdout)
    h_match = re.search(r"pixelHeight:\s*(\d+)", proc.stdout)
    if not w_match or not h_match:
        raise ValueError(f"Could not parse image dimensions from sips output for {path}")
    return int(w_match.group(1)), int(h_match.group(1))


def _extract_pdf(path: Path) -> tuple[str, dict[str, Any], bool]:
    if PdfReader is not None:
        reader = PdfReader(str(path))
        pages_text: list[str] = []
        for p_idx, page in enumerate(reader.pages, start=1):
            p_txt = (page.extract_text() or "").strip()
            if p_txt:
                pages_text.append(f"#### Page {p_idx}\n\n{p_txt}")
        joined = "\n\n".join(pages_text)
        return joined, {"pages": len(reader.pages)}, not bool(joined.strip())

    pdftotext_bin = shutil.which("pdftotext")
    if pdftotext_bin:
        proc = subprocess.run(
            [pdftotext_bin, str(path.resolve()), "-"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        txt = proc.stdout.strip()
        return txt, {}, not bool(txt)

    return "", {}, True


def _is_brand_logo_rel_path(rel_path: str) -> bool:
    return rel_path.strip("/").lower() == "logo.png"


def _extract_single_file(path: Path, rel_path: str) -> dict[str, Any]:
    ext = path.suffix.lower()
    is_logo = _is_brand_logo_rel_path(rel_path)
    entry: dict[str, Any] = {
        "rel_path": rel_path,
        "abs_path": str(path.resolve()),
        "kind": "unsupported",
        "role": "brand_logo" if is_logo else "source_content",
        "status": "ok",
        "needs_multimodal_view": False,
        "extracted_text": "",
        "metadata": {},
        "error": None,
    }
    try:
        if ext in TEXT_EXTS:
            entry["kind"] = "text"
            entry["extracted_text"] = path.read_text(encoding="utf-8-sig", errors="replace").strip()
        elif ext in CSV_EXTS:
            entry["kind"] = "csv"
            delim = "\t" if ext == ".tsv" else ","
            raw = path.read_text(encoding="utf-8-sig", errors="replace")
            rows = list(csv.reader(io.StringIO(raw), delimiter=delim))
            entry["extracted_text"] = _markdown_table(rows)
            entry["metadata"] = {"rows": len(rows)}
        elif ext == ".eml":
            entry["kind"] = "email"
            text, meta = _extract_eml(path)
            entry["extracted_text"] = text
            entry["metadata"] = meta
        elif ext == ".msg":
            entry["kind"] = "email"
            text, meta = _extract_msg(path)
            entry["extracted_text"] = text
            entry["metadata"] = meta
        elif ext == ".docx":
            entry["kind"] = "docx"
            text, meta = _extract_docx(path)
            entry["extracted_text"] = text
            entry["metadata"] = meta
        elif ext in {".doc", ".rtf"}:
            entry["kind"] = "docx"
            proc = subprocess.run(
                ["/usr/bin/textutil", "-convert", "txt", "-stdout", str(path.resolve())],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            entry["extracted_text"] = proc.stdout.strip()
        elif ext == ".xlsx":
            entry["kind"] = "xlsx"
            text, meta = _extract_xlsx(path)
            entry["extracted_text"] = text
            entry["metadata"] = meta
        elif ext == ".pptx":
            entry["kind"] = "pptx"
            text, meta = _extract_pptx(path)
            entry["extracted_text"] = text
            entry["metadata"] = meta
        elif ext == ".pdf":
            entry["kind"] = "pdf"
            text, meta, needs_mm = _extract_pdf(path)
            entry["extracted_text"] = text
            entry["metadata"] = meta
            entry["needs_multimodal_view"] = needs_mm
        elif ext in IMAGE_EXTS:
            entry["kind"] = "image"
            w, h = _image_dimensions(path)
            entry["metadata"] = {"width": w, "height": h}
            entry["needs_multimodal_view"] = not is_logo
        else:
            entry["kind"] = "unsupported"
            entry["status"] = "unsupported"
            return entry

        if entry["kind"] != "image" and not entry["extracted_text"].strip():
            entry["status"] = "empty_or_scanned"
    except Exception as exc:
        entry["status"] = "error"
        entry["error"] = str(exc)
    return entry


def _render_digest_markdown(assets_dir: Path, files: list[dict[str, Any]]) -> str:
    logo_entries = [f for f in files if f.get("role") == "brand_logo"]
    lines = [
        "# Extracted Source Assets Digest",
        "",
        f"- **Source Directory:** `{assets_dir.resolve()}`",
        "- **Excluded Style Reference Directory:** `assets/XPLANE/` (never treated as topic content)",
        f"- **Discovered Source Files:** {len(files)}",
        "",
    ]
    if logo_entries:
        logo = logo_entries[0]
        lines.extend(
            [
                "## Mandatory Brand Logo (`assets/logo.png`)",
                "",
                f"- **Logo File:** `{logo['abs_path']}` — metadata: `{json.dumps(logo['metadata'])}`",
                "- **Rule:** Always use `assets/logo.png` verbatim as the sole brand logo on every generated infographic regardless of what image it contains. Leave the reserved masthead logo zone (`top-right`, `x = 82%..98%, y = 0%..10.5%`) completely empty in the prompt (zero AI-drawn logos or icons in the masthead) so `render_infographic_4k.py` composites `assets/logo.png` cleanly at appropriate scale.",
                "",
            ]
        )
    multimodal = [f for f in files if f["needs_multimodal_view"]]
    if multimodal:
        lines.append("## Files Requiring Direct Multimodal `read_file` Inspection")
        lines.append("")
        for f in multimodal:
            lines.append(
                f"- `{f['rel_path']}` (`{f['abs_path']}`) — kind: `{f['kind']}`, metadata: `{json.dumps(f['metadata'])}`"
            )
        lines.append("")

    lines.append("## Extracted Text & Tabular Content")
    lines.append("")
    for f in files:
        lines.append(f"### `{f['rel_path']}` (`{f['kind']}` — status: `{f['status']}`)")
        lines.append("")
        if f["error"]:
            lines.append(f"> Extraction error: `{f['error']}`")
            lines.append("")
        elif f["extracted_text"]:
            lines.append(f["extracted_text"])
            lines.append("")
        elif f["needs_multimodal_view"]:
            lines.append(f"*Visual/scanned asset — inspect `{f['abs_path']}` directly with `read_file`.*")
            lines.append("")
        else:
            lines.append("*No extractable text.*")
            lines.append("")
    return "\n".join(lines)


def _is_within_allowed_assets_tree(candidate: Path, assets_root: Path, forbidden_roots: list[Path]) -> bool:
    try:
        resolved = candidate.resolve()
    except OSError:
        return False
    if not resolved.is_relative_to(assets_root):
        return False
    for forbidden in forbidden_roots:
        if resolved.is_relative_to(forbidden):
            return False
    return True


def ingest_assets(assets_dir: Path, out_dir: Path | None = None) -> dict[str, Any]:
    assets_dir = Path(assets_dir)
    discovered: list[Path] = []

    if assets_dir.is_dir():
        assets_root = assets_dir.resolve()
        forbidden_roots = [
            child.resolve()
            for child in assets_dir.iterdir()
            if child.is_dir() and child.name.lower() == "xplane"
        ]
        for root_str, dirnames, filenames in os.walk(assets_dir, followlinks=False):
            root_path = Path(root_str)
            is_top = root_path.resolve() == assets_root
            kept_dirs: list[str] = []
            for d in sorted(dirnames):
                if _should_skip_name(d):
                    continue
                if is_top and d.lower() == "xplane":
                    continue
                d_path = root_path / d
                if d_path.is_symlink() or not _is_within_allowed_assets_tree(d_path, assets_root, forbidden_roots):
                    continue
                kept_dirs.append(d)
            dirnames[:] = kept_dirs

            for fname in sorted(filenames):
                if _should_skip_name(fname):
                    continue
                f_path = root_path / fname
                if not _is_within_allowed_assets_tree(f_path, assets_root, forbidden_roots):
                    continue
                discovered.append(f_path)

    discovered.sort(key=lambda p: p.relative_to(assets_dir).as_posix())
    entries = [
        _extract_single_file(p, p.relative_to(assets_dir).as_posix())
        for p in discovered
    ]

    md_path_str: str | None = None
    json_path_str: str | None = None
    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        md_path = out_dir / "digest.md"
        json_path = out_dir / "manifest.json"
        md_path.write_text(_render_digest_markdown(assets_dir, entries), encoding="utf-8")
        md_path_str = str(md_path.resolve())
        json_path_str = str(json_path.resolve())

    logo_entry = next((f for f in entries if f.get("role") == "brand_logo"), None)
    result: dict[str, Any] = {
        "assets_dir": str(assets_dir.resolve()),
        "excluded_dirs": ["XPLANE"],
        "logo_path": logo_entry["abs_path"] if logo_entry else None,
        "file_count": len(entries),
        "files": entries,
        "markdown_digest_path": md_path_str,
        "json_manifest_path": json_path_str,
    }
    if out_dir is not None and json_path_str is not None:
        Path(json_path_str).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest source files from assets/ excluding assets/XPLANE/.")
    parser.add_argument(
        "--assets-dir",
        type=Path,
        default=REPO_ROOT / "assets",
        help="Path to assets directory (default: <repo>/assets)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=REPO_ROOT / ".scratch" / "extracted-assets",
        help="Directory to write manifest.json and digest.md",
    )
    args = parser.parse_args()
    result = ingest_assets(args.assets_dir, args.out_dir)
    summary = {
        "assets_dir": result["assets_dir"],
        "excluded_dirs": result["excluded_dirs"],
        "logo_path": result["logo_path"],
        "file_count": result["file_count"],
        "markdown_digest_path": result["markdown_digest_path"],
        "json_manifest_path": result["json_manifest_path"],
        "files": [
            {
                "rel_path": f["rel_path"],
                "abs_path": f["abs_path"],
                "kind": f["kind"],
                "role": f["role"],
                "status": f["status"],
                "needs_multimodal_view": f["needs_multimodal_view"],
                "metadata": f["metadata"],
                "error": f["error"],
            }
            for f in result["files"]
        ],
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
