import email.message
import importlib.util
import struct
import zipfile
from pathlib import Path
from PIL import Image
from pptx import Presentation
from pptx.util import Inches
from pypdf import PdfWriter

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / ".agents/skills/xplane-infographic-studio/scripts/ingest_assets.py"


def load_module():
    spec = importlib.util.spec_from_file_location("ingest_assets", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_minimal_docx(path: Path, text: str) -> None:
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("word/document.xml", xml)


def _make_minimal_xlsx(path: Path, header: str, value: str) -> None:
    workbook = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheets><sheet name="KPIs" sheetId="1" r:id="rId1" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/></sheets></workbook>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/></Relationships>'
    )
    shared = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<si><t>{header}</t></si></sst>"
    )
    sheet = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData><row r="1"><c r="A1" t="s"><v>0</v></c>'
        f'<c r="B1"><v>{value}</v></c></row></sheetData></worksheet>'
    )
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", rels)
        zf.writestr("xl/sharedStrings.xml", shared)
        zf.writestr("xl/worksheets/sheet1.xml", sheet)


def test_excludes_xplane_dir_and_recurses_user_subdirs(tmp_path: Path):
    mod = load_module()
    assets = tmp_path / "assets"
    (assets / "XPLANE").mkdir(parents=True)
    (assets / "XPLANE" / "secret_canon.txt").write_text("ALVARIA CANON DO NOT LEAK", encoding="utf-8")
    (assets / "sub" / "nested").mkdir(parents=True)
    (assets / "sub" / "nested" / "brief.md").write_text("# Cloud Migration\n90% faster", encoding="utf-8")

    result = mod.ingest_assets(assets, tmp_path / "out")
    rel_paths = [f["rel_path"] for f in result["files"]]
    assert rel_paths == ["sub/nested/brief.md"]
    digest = Path(result["markdown_digest_path"]).read_text(encoding="utf-8")
    assert "ALVARIA CANON" not in digest
    assert "90% faster" in digest


def test_skips_hidden_and_office_lockfiles(tmp_path: Path):
    mod = load_module()
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / ".DS_Store").write_bytes(b"\x00\x01bad")
    (assets / "~$open_sheet.xlsx").write_bytes(b"not a zip")
    (assets / "notes.txt").write_text("Valid note", encoding="utf-8")

    result = mod.ingest_assets(assets)
    assert [f["rel_path"] for f in result["files"]] == ["notes.txt"]


def test_extracts_docx_xlsx_pptx_eml_csv_and_images(tmp_path: Path):
    mod = load_module()
    assets = tmp_path / "assets"
    assets.mkdir()
    _make_minimal_docx(assets / "spec.docx", "Zero Shadow Access Policy")
    _make_minimal_xlsx(assets / "metrics.xlsx", "TokenSavings", "85")

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = "Architecture Roadmap"
    prs.save(assets / "deck.pptx")

    msg = email.message.EmailMessage()
    msg["Subject"] = "Exec Sponsors"
    msg["From"] = "cto@example.com"
    msg.set_content("Approved for 60-day rollout.")
    (assets / "kickoff.eml").write_bytes(msg.as_bytes())

    (assets / "stages.csv").write_text("stage,days\nIntake,5\n", encoding="utf-8")
    Image.new("RGB", (320, 180), "white").save(assets / "diagram.png")

    result = mod.ingest_assets(assets)
    by_name = {f["rel_path"]: f for f in result["files"]}
    assert "Zero Shadow Access Policy" in by_name["spec.docx"]["extracted_text"]
    assert "TokenSavings" in by_name["metrics.xlsx"]["extracted_text"]
    assert "85" in by_name["metrics.xlsx"]["extracted_text"]
    assert "Architecture Roadmap" in by_name["deck.pptx"]["extracted_text"]
    assert "Exec Sponsors" in by_name["kickoff.eml"]["extracted_text"]
    assert "Approved for 60-day rollout." in by_name["kickoff.eml"]["extracted_text"]
    assert "Intake" in by_name["stages.csv"]["extracted_text"]
    assert by_name["diagram.png"]["needs_multimodal_view"] is True
    assert by_name["diagram.png"]["metadata"] == {"width": 320, "height": 180}


def test_image_only_pdf_flags_multimodal_view(tmp_path: Path):
    mod = load_module()
    assets = tmp_path / "assets"
    assets.mkdir()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with (assets / "scanned.pdf").open("wb") as fh:
        writer.write(fh)

    result = mod.ingest_assets(assets)
    pdf_entry = result["files"][0]
    assert pdf_entry["kind"] == "pdf"
    assert pdf_entry["status"] == "empty_or_scanned"
    assert pdf_entry["needs_multimodal_view"] is True


def test_corrupt_or_unsupported_file_does_not_abort_batch(tmp_path: Path):
    mod = load_module()
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "broken.docx").write_bytes(b"corrupt-zip-bytes")
    (assets / "archive.bin").write_bytes(b"\x89\x00\xff")
    (assets / "good.txt").write_text("Still extracted", encoding="utf-8")

    result = mod.ingest_assets(assets)
    by_name = {f["rel_path"]: f for f in result["files"]}
    assert by_name["broken.docx"]["status"] == "error"
    assert by_name["archive.bin"]["status"] == "unsupported"
    assert by_name["good.txt"]["status"] == "ok"


def _make_minimal_cfb_msg(path: Path, subject: str, sender: str, body_long: str) -> None:
    """Build a valid MS-CFB v3 .msg file exercising BOTH MiniStream (<4096B) and regular FAT (>=4096B)."""
    end_of_chain = 0xFFFFFFFE
    free_sect = 0xFFFFFFFF
    fat_sect = 0xFFFFFFFD

    subj_bytes = subject.encode("utf-16-le")      # < 4096 -> stored in MiniStream (64B mini-sectors)
    from_bytes = sender.encode("utf-16-le")       # < 4096 -> stored in MiniStream
    body_bytes = body_long.encode("utf-16-le")    # >= 4096 -> stored in regular 512B sectors
    assert len(body_bytes) >= 4096

    def pad(b: bytes, block: int) -> bytes:
        rem = len(b) % block
        return b if rem == 0 else b + b"\x00" * (block - rem)

    subj_mini = pad(subj_bytes, 64)
    from_mini = pad(from_bytes, 64)
    n_subj_mini = len(subj_mini) // 64
    n_from_mini = len(from_mini) // 64
    mini_stream = pad(subj_mini + from_mini, 512)
    n_mini_stream_secs = len(mini_stream) // 512

    minifat_entries = (
        [i + 1 for i in range(n_subj_mini - 1)] + [end_of_chain]
        + [n_subj_mini + i + 1 for i in range(n_from_mini - 1)] + [end_of_chain]
    )
    minifat_sector = pad(struct.pack(f"<{len(minifat_entries)}I", *minifat_entries), 512)
    assert len(minifat_sector) == 512

    body_padded = pad(body_bytes, 512)
    n_body_secs = len(body_padded) // 512

    def dir_entry(name: str, obj_type: int, start_sec: int, size: int, left: int = 0xFFFFFFFF, right: int = 0xFFFFFFFF, child: int = 0xFFFFFFFF) -> bytes:
        raw_name = (name + "\x00").encode("utf-16-le")
        buf = bytearray(128)
        buf[:len(raw_name)] = raw_name
        struct.pack_into("<HBBIII", buf, 64, len(raw_name), obj_type, 1, left, right, child)
        struct.pack_into("<II", buf, 116, start_sec, size)
        return bytes(buf)

    # Sector layout:
    # 0: FAT, 1: Directory, 2: MiniFAT, 3..(3+n_mini_stream_secs-1): MiniStream, next..: Body regular sectors
    sec_minifat = 2
    sec_ministream = 3
    sec_body = sec_ministream + n_mini_stream_secs

    entries = [
        dir_entry("Root Entry", 5, sec_ministream, len(subj_mini) + len(from_mini), child=1),
        dir_entry("__substg1.0_0037001F", 2, 0, len(subj_bytes), right=2),
        dir_entry("__substg1.0_0C1A001F", 2, n_subj_mini, len(from_bytes), right=3),
        dir_entry("__substg1.0_1000001F", 2, sec_body, len(body_bytes)),
    ]
    dir_sector = b"".join(entries)  # 4 * 128 = 512 bytes

    fat = [fat_sect, end_of_chain, end_of_chain]  # sec 0 (FAT), sec 1 (Dir), sec 2 (MiniFAT)
    fat += [sec_ministream + i + 1 for i in range(n_mini_stream_secs - 1)] + [end_of_chain]
    fat += [sec_body + i + 1 for i in range(n_body_secs - 1)] + [end_of_chain]
    fat += [free_sect] * (128 - len(fat))
    fat_sector = struct.pack("<128I", *fat)

    header = bytearray(512)
    header[:8] = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    struct.pack_into("<HH", header, 24, 0x003E, 0x0003)
    struct.pack_into("<HHH", header, 28, 0xFFFE, 9, 6)
    struct.pack_into("<IIIIIIII", header, 44, 1, 1, 0, 4096, sec_minifat, 1, end_of_chain, 0)
    struct.pack_into("<I", header, 76, 0)  # DIFAT[0] = sector 0
    for idx in range(1, 109):
        struct.pack_into("<I", header, 76 + idx * 4, free_sect)

    path.write_bytes(bytes(header) + fat_sector + dir_sector + minifat_sector + mini_stream + body_padded)


def test_extracts_outlook_msg_ole2_file(tmp_path: Path):
    mod = load_module()
    assets = tmp_path / "assets"
    assets.mkdir()
    long_body = "Architecture ARB Gate approved. " * 90  # > 4096 bytes in UTF-16LE
    _make_minimal_cfb_msg(assets / "approval.msg", "Q4 Cloud Signoff", "vp-eng@example.com", long_body)

    result = mod.ingest_assets(assets)
    entry = result["files"][0]
    assert entry["kind"] == "email"
    assert entry["status"] == "ok"
    assert "Q4 Cloud Signoff" in entry["extracted_text"]
    assert "vp-eng@example.com" in entry["extracted_text"]
    assert "Architecture ARB Gate approved." in entry["extracted_text"]


def test_extracts_grouped_pptx_shapes_and_docx_sdt_controls(tmp_path: Path):
    mod = load_module()
    assets = tmp_path / "assets"
    assets.mkdir()

    # .docx with <w:sdt><w:sdtContent> wrapper
    sdt_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:sdt><w:sdtContent>"
        "<w:p><w:r><w:t>SDT Wrapped Control Requirement</w:t></w:r></w:p>"
        "</w:sdtContent></w:sdt></w:body></w:document>"
    )
    with zipfile.ZipFile(assets / "sdt.docx", "w") as zf:
        zf.writestr("word/document.xml", sdt_xml)

    # .pptx with a GroupShape containing nested text shapes, plus a blank slide deck
    prs = Presentation()
    blank_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank_layout)
    grp = slide.shapes.add_group_shape()
    tb = grp.shapes.add_textbox(Inches(1), Inches(1), Inches(3), Inches(1))
    tb.text_frame.text = "Nested Swimlane Node"
    prs.save(assets / "grouped.pptx")

    empty_prs = Presentation()
    empty_prs.slides.add_slide(empty_prs.slide_layouts[6])
    empty_prs.save(assets / "visual_only.pptx")

    result = mod.ingest_assets(assets)
    by_name = {f["rel_path"]: f for f in result["files"]}
    assert "SDT Wrapped Control Requirement" in by_name["sdt.docx"]["extracted_text"]
    assert "Nested Swimlane Node" in by_name["grouped.pptx"]["extracted_text"]
    assert by_name["visual_only.pptx"]["status"] == "empty_or_scanned"


def test_stdlib_pptx_and_sips_fallbacks_when_optional_libs_absent(tmp_path: Path, monkeypatch):
    mod = load_module()
    assets = tmp_path / "assets"
    assets.mkdir()

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    grp = slide.shapes.add_group_shape()
    grp.shapes.add_textbox(Inches(1), Inches(1), Inches(2), Inches(1)).text_frame.text = "Stdlib XML Fallback Text"
    prs.save(assets / "fallback.pptx")

    Image.new("RGB", (240, 120), "white").save(assets / "pic.png")
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with (assets / "doc.pdf").open("wb") as fh:
        writer.write(fh)

    monkeypatch.setattr(mod, "Presentation", None)
    monkeypatch.setattr(mod, "Image", None)
    monkeypatch.setattr(mod, "PdfReader", None)

    result = mod.ingest_assets(assets)
    by_name = {f["rel_path"]: f for f in result["files"]}
    assert "Stdlib XML Fallback Text" in by_name["fallback.pptx"]["extracted_text"]
    assert by_name["pic.png"]["metadata"] == {"width": 240, "height": 120}
    assert by_name["pic.png"]["needs_multimodal_view"] is True
    assert by_name["doc.pdf"]["needs_multimodal_view"] is True


def test_symlink_into_xplane_or_outside_assets_is_blocked(tmp_path: Path):
    mod = load_module()
    assets = tmp_path / "assets"
    (assets / "XPLANE").mkdir(parents=True)
    canon = assets / "XPLANE" / "canon.txt"
    canon.write_text("CANON SECRET", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("OUTSIDE SECRET", encoding="utf-8")

    (assets / "sneaky_canon.txt").symlink_to(canon)
    (assets / "sneaky_outside.txt").symlink_to(outside)
    (assets / "legit.txt").write_text("Safe content", encoding="utf-8")

    result = mod.ingest_assets(assets)
    assert [f["rel_path"] for f in result["files"]] == ["legit.txt"]

