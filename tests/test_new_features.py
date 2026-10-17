from __future__ import annotations

import builtins
import io
import logging
import shutil
import sys
from pathlib import Path

import pytest

# pdfsuite lives in ../src, which is not on sys.path for `python tests/...` or pytest.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pdfsuite  # noqa: E402

pymupdf = pytest.importorskip("pymupdf")
pypdf = pytest.importorskip("pypdf")
Image = pytest.importorskip("PIL.Image")


# --- helpers ----------------------------------------------------------------


def make_pdf(path: Path, pages: int = 3, label: str = "doc", sizes: list[tuple[float, float]] | None = None) -> Path:
    """Write a PDF whose page i (1-based) contains the text "<label> page <i>"."""
    doc = pymupdf.open()
    for i in range(1, pages + 1):
        w, h = sizes[i - 1] if sizes else (595, 842)
        doc.new_page(width=w, height=h).insert_text((72, 72), f"{label} page {i}", fontsize=14)
    doc.save(str(path))
    return path


def page_texts(path: Path) -> list[str]:
    with pymupdf.open(str(path)) as doc:
        return [" ".join(page.get_text("text").split()) for page in doc]


def page_sizes(path: Path) -> list[tuple[int, int]]:
    with pymupdf.open(str(path)) as doc:
        return [(round(p.rect.width), round(p.rect.height)) for p in doc]


def feed_input(monkeypatch, answers: list[str]) -> None:
    it = iter(answers)
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(it))


needs_ocr_tools = pytest.mark.skipif(
    not (shutil.which("tesseract") and shutil.which("gs")), reason="needs Tesseract and Ghostscript"
)


# --- images to PDF ------------------------------------------------------------


def _save(img, path: Path, **kw) -> Path:
    img.save(path, **kw)
    return path


def test_images_all_types_in_natural_order(tmp_path) -> None:
    # Heights identify each image's page: 10, 20, 30, ...
    files = {
        "p1.jpg": "JPEG",
        "p2.png": "PNG",
        "p3.bmp": "BMP",
        "p4.gif": "GIF",
        "p5.webp": "WEBP",
        "p6.tiff": "TIFF",
        "p10.PNG": "PNG",
    }
    for i, (name, fmt) in enumerate(files.items(), start=1):
        _save(Image.new("RGB", (100, 10 * i), (i * 30, 100, 100)), tmp_path / name, format=fmt)
    (tmp_path / "notes.txt").write_text("not an image")

    assert pdfsuite.images_to_pdf(tmp_path, output_pdf="all.pdf")
    with pymupdf.open(str(tmp_path / "all.pdf")) as doc:
        heights = [round(p.rect.height / p.rect.width * 100) for p in doc]
    assert heights == [10, 20, 30, 40, 50, 60, 70]


def test_images_jpeg_embedded_unchanged(tmp_path) -> None:
    src = _save(Image.effect_noise((64, 48), 50).convert("RGB"), tmp_path / "photo.jpg", format="JPEG", quality=80)
    assert pdfsuite.images_to_pdf(tmp_path, ["photo.jpg"], "out.pdf")
    with pymupdf.open(str(tmp_path / "out.pdf")) as doc:
        xref = doc[0].get_images()[0][0]
        assert doc.extract_image(xref)["image"] == src.read_bytes()


def test_images_png_pixels_kept(tmp_path) -> None:
    img = Image.effect_noise((40, 30), 80).convert("RGB")
    _save(img, tmp_path / "a.png", format="PNG")
    assert pdfsuite.images_to_pdf(tmp_path, ["a.png"], "out.pdf")
    with pymupdf.open(str(tmp_path / "out.pdf")) as doc:
        data = doc.extract_image(doc[0].get_images()[0][0])["image"]
    assert Image.open(io.BytesIO(data)).convert("RGB").tobytes() == img.tobytes()


def test_images_transparency_becomes_white(tmp_path) -> None:
    img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))  # fully transparent...
    img.paste((255, 0, 0, 255), (0, 0, 50, 100))  # ...except a red left half
    _save(img, tmp_path / "t.png", format="PNG")
    assert pdfsuite.images_to_pdf(tmp_path, ["t.png"], "out.pdf")
    with pymupdf.open(str(tmp_path / "out.pdf")) as doc:
        pix = doc[0].get_pixmap()
    w, h = pix.width, pix.height
    assert pix.pixel(w // 4, h // 2)[:3] == (255, 0, 0)
    assert pix.pixel(3 * w // 4, h // 2)[:3] == (255, 255, 255)


def test_images_multipage_tiff(tmp_path) -> None:
    frames = [Image.new("RGB", (50, 50), c) for c in ("red", "green", "blue")]
    frames[0].save(tmp_path / "scan.tif", save_all=True, append_images=frames[1:])
    assert pdfsuite.images_to_pdf(tmp_path, ["scan.tif"], "out.pdf")
    assert len(page_sizes(tmp_path / "out.pdf")) == 3


def test_images_heic(tmp_path) -> None:
    pi_heif = pytest.importorskip("pi_heif")
    pi_heif.register_heif_opener()
    try:
        _save(Image.new("RGB", (64, 32), "orange"), tmp_path / "phone.heic", format="HEIF")
    except Exception as exc:  # pragma: no cover - depends on the libheif build
        pytest.skip(f"cannot write HEIC here: {exc}")
    assert pdfsuite.images_to_pdf(tmp_path, ["phone.heic"], "out.pdf")
    assert page_sizes(tmp_path / "out.pdf")[0][0] == 2 * page_sizes(tmp_path / "out.pdf")[0][1]


def test_images_corrupt_file_fails_cleanly(tmp_path) -> None:
    _save(Image.new("RGB", (10, 10)), tmp_path / "good.png", format="PNG")
    (tmp_path / "bad.webp").write_bytes(b"not really an image")
    assert not pdfsuite.images_to_pdf(tmp_path, output_pdf="out.pdf")
    assert not (tmp_path / "out.pdf").exists()


def test_images_empty_folder_and_missing_file(tmp_path) -> None:
    assert not pdfsuite.images_to_pdf(tmp_path, output_pdf="out.pdf")
    _save(Image.new("RGB", (10, 10)), tmp_path / "a.png", format="PNG")
    assert not pdfsuite.images_to_pdf(tmp_path, ["a.png", "nope.png"], "out.pdf")
    assert not (tmp_path / "out.pdf").exists()


def test_images_cli_new_and_old_names(tmp_path) -> None:
    _save(Image.new("RGB", (10, 10)), tmp_path / "a.png", format="PNG")
    assert pdfsuite.main(["images-to-pdf", "--folder", str(tmp_path), "--out", "new.pdf"]) == 0
    assert pdfsuite.main(["jpg-merge", "--folder", str(tmp_path), "--out", "old.pdf"]) == 0
    assert (tmp_path / "new.pdf").exists() and (tmp_path / "old.pdf").exists()
    # The old function name still works too.
    assert pdfsuite.jpeg_to_pdf_merge(tmp_path, jpg_files=["a.png"], output_pdf="fn.pdf")


# --- insert pages -------------------------------------------------------------


@pytest.fixture
def three(tmp_path) -> Path:
    return make_pdf(tmp_path / "in.pdf", 3, sizes=[(595, 842), (842, 595), (300, 400)])


def test_insert_blank_pages_after_page(tmp_path, three) -> None:
    out = tmp_path / "o.pdf"
    assert pdfsuite.insert_pages_pdf(three, out, after=2, blank_count=2)
    assert page_texts(out) == ["doc page 1", "doc page 2", "", "", "doc page 3"]
    # Blank pages take the size of the page they follow (landscape page 2).
    assert page_sizes(out)[2:4] == [(842, 595), (842, 595)]


@pytest.mark.parametrize(("after", "expected_blank_index"), [(0, 0), (3, 3)])
def test_insert_blank_at_start_and_end(tmp_path, three, after, expected_blank_index) -> None:
    out = tmp_path / "o.pdf"
    assert pdfsuite.insert_pages_pdf(three, out, after=after)
    texts = page_texts(out)
    assert len(texts) == 4 and texts[expected_blank_index] == ""
    # At the start, the blank page takes page 1's size.
    if after == 0:
        assert page_sizes(out)[0] == (595, 842)


def test_insert_pages_from_other_pdf(tmp_path, three) -> None:
    other = make_pdf(tmp_path / "other.pdf", 4, "X")
    out = tmp_path / "o.pdf"
    assert pdfsuite.insert_pages_pdf(three, out, after=1, source_pdf=other, source_pages="4,2")
    assert page_texts(out) == ["doc page 1", "X page 4", "X page 2", "doc page 2", "doc page 3"]

    out_all = tmp_path / "all.pdf"
    assert pdfsuite.insert_pages_pdf(three, out_all, after=3, source_pdf=other)
    assert len(page_texts(out_all)) == 7


def test_insert_keeps_bookmarks_on_their_pages(tmp_path, three) -> None:
    with pymupdf.open(str(three)) as doc:
        doc.set_toc([[1, "Start", 1], [1, "End", 3]])
        doc.save(str(tmp_path / "bm.pdf"))
    out = tmp_path / "o.pdf"
    assert pdfsuite.insert_pages_pdf(tmp_path / "bm.pdf", out, after=1, blank_count=2)
    assert pdfsuite.get_bookmarks(out) == [(1, "Start", 1), (1, "End", 5)]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"after": -1},
        {"after": 4},
        {"after": 1, "blank_count": 0},
        {"after": 1, "source_pdf": "missing.pdf"},
        {"after": 1, "source_pdf": "SELF", "source_pages": "9"},
    ],
)
def test_insert_invalid_requests(tmp_path, three, kwargs) -> None:
    if kwargs.get("source_pdf") == "SELF":
        kwargs["source_pdf"] = three
    elif "source_pdf" in kwargs:
        kwargs["source_pdf"] = tmp_path / kwargs["source_pdf"]
    out = tmp_path / "o.pdf"
    assert not pdfsuite.insert_pages_pdf(three, out, **kwargs)
    assert not out.exists()


def test_insert_cli_and_menu(tmp_path, three, monkeypatch) -> None:
    other = make_pdf(tmp_path / "other.pdf", 2, "X")
    assert pdfsuite.main(["insert-pages", "--in", str(three), "--out", str(tmp_path / "c.pdf"), "--after", "3", "--blank", "1"]) == 0
    assert len(page_texts(tmp_path / "c.pdf")) == 4

    feed_input(monkeypatch, ["24", str(three), str(tmp_path / "m.pdf"), "0", "y", str(other), "2", "", "0"])
    assert pdfsuite.interactive_menu() == 0
    assert page_texts(tmp_path / "m.pdf")[0] == "X page 2"

    feed_input(monkeypatch, ["24", str(three), str(tmp_path / "m2.pdf"), "1", "n", "3", "", "0"])
    assert pdfsuite.interactive_menu() == 0
    assert len(page_texts(tmp_path / "m2.pdf")) == 6


# --- bookmarks ----------------------------------------------------------------


@pytest.fixture
def ten(tmp_path) -> Path:
    return make_pdf(tmp_path / "ten.pdf", 10)


def _with_toc(src: Path, dst: Path, toc: list[list]) -> Path:
    with pymupdf.open(str(src)) as doc:
        doc.set_toc(toc)
        doc.save(str(dst))
    return dst


def test_bookmarks_none(ten) -> None:
    assert pdfsuite.get_bookmarks(ten) == []
    assert pdfsuite.show_bookmarks(ten)


def test_add_bookmark_keeps_page_order_and_children(tmp_path, ten) -> None:
    src = _with_toc(ten, tmp_path / "bm.pdf", [[1, "A", 1], [2, "A.1", 2], [1, "B", 5]])
    out1, out2 = tmp_path / "o1.pdf", tmp_path / "o2.pdf"
    assert pdfsuite.add_bookmark(src, out1, "Middle", 3)
    assert pdfsuite.add_bookmark(out1, out2, "  Last ", 9)
    assert pdfsuite.get_bookmarks(out2) == [
        (1, "A", 1),
        (2, "A.1", 2),
        (1, "Middle", 3),
        (1, "B", 5),
        (1, "Last", 9),
    ]


@pytest.mark.parametrize(("title", "page"), [("", 1), ("   ", 1), ("X", 0), ("X", 11)])
def test_add_bookmark_invalid(tmp_path, ten, title, page) -> None:
    out = tmp_path / "o.pdf"
    assert not pdfsuite.add_bookmark(ten, out, title, page)
    assert not out.exists()


def test_bookmarks_export_import_roundtrip(tmp_path, ten) -> None:
    toc = [[1, "Intro", 1], [1, "Chapter 1", 2], [2, "Section 1.1", 3], [3, "Deep", 4], [1, "Ünïcode ✓", 10]]
    src = _with_toc(ten, tmp_path / "bm.pdf", toc)
    txt = tmp_path / "bm.txt"
    assert pdfsuite.export_bookmarks(src, txt)
    content = txt.read_text(encoding="utf-8")
    assert "\n    4 Deep\n" in content and content.startswith("# JAP-T bookmarks")

    out = tmp_path / "copy.pdf"
    assert pdfsuite.import_bookmarks(ten, out, txt)
    assert pdfsuite.get_bookmarks(out) == [tuple(t) for t in toc]
    assert page_texts(out) == page_texts(ten)  # pages untouched


def test_import_accepts_notepad_files(tmp_path, ten) -> None:
    txt = tmp_path / "bm.txt"
    # Byte-order mark, Windows line endings, tabs, blank lines and comments.
    txt.write_bytes("﻿# comment\r\n1 First\r\n\t2 Child\r\n\r\n  3 Also child\r\n5 Second\r\n".encode("utf-8"))
    out = tmp_path / "o.pdf"
    assert pdfsuite.import_bookmarks(ten, out, txt)
    assert pdfsuite.get_bookmarks(out) == [(1, "First", 1), (2, "Child", 2), (2, "Also child", 3), (1, "Second", 5)]


def test_import_empty_file_removes_bookmarks(tmp_path, ten) -> None:
    src = _with_toc(ten, tmp_path / "bm.pdf", [[1, "A", 1]])
    txt = tmp_path / "empty.txt"
    txt.write_text("# nothing here\n")
    out = tmp_path / "o.pdf"
    assert pdfsuite.import_bookmarks(src, out, txt)
    assert pdfsuite.get_bookmarks(out) == []


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("1 A\nx B\n", "line 2: expected"),
        ("1 A\n2\n", "line 2: expected"),
        ("1 A\n11 B\n", "line 2: page 11 is out of range"),
        ("1 A\n    2 B\n", "line 2: indented too far"),
        ("  1 A\n", "line 1: indented too far"),
    ],
)
def test_import_reports_bad_line(tmp_path, ten, caplog, text, message) -> None:
    txt = tmp_path / "bm.txt"
    txt.write_text(text)
    out = tmp_path / "o.pdf"
    assert not pdfsuite.import_bookmarks(ten, out, txt)
    assert message in caplog.text
    assert not out.exists()


def test_bookmarks_cli(tmp_path, ten) -> None:
    out, txt, back = tmp_path / "o.pdf", tmp_path / "b.txt", tmp_path / "back.pdf"
    assert pdfsuite.main(["bookmarks-add", "--in", str(ten), "--out", str(out), "--title", "Cover", "--page", "1"]) == 0
    assert pdfsuite.main(["bookmarks-show", "--in", str(out)]) == 0
    assert pdfsuite.main(["bookmarks-export", "--in", str(out), "--out", str(txt)]) == 0
    assert pdfsuite.main(["bookmarks-import", "--in", str(ten), "--out", str(back), "--file", str(txt)]) == 0
    assert pdfsuite.get_bookmarks(back) == [(1, "Cover", 1)]


def test_bookmarks_menu(tmp_path, ten, monkeypatch) -> None:
    out, txt, back = tmp_path / "o.pdf", tmp_path / "b.txt", tmp_path / "back.pdf"
    feed_input(
        monkeypatch,
        [
            "25", "add", str(ten), str(out), "Chapter", "4", "",
            "25", "show", str(out), "",
            "25", "export", str(out), str(txt), "",
            "25", "import", str(ten), str(txt), str(back), "",
            "0",
        ],
    )
    assert pdfsuite.interactive_menu() == 0
    assert pdfsuite.get_bookmarks(back) == [(1, "Chapter", 4)]


# --- redaction ----------------------------------------------------------------


@pytest.fixture
def letter(tmp_path) -> Path:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 100), "Name: John Smith", fontsize=14)
    page.insert_text((72, 130), "Account 12345678 is SECRET", fontsize=14)
    page.insert_text((72, 160), "Keep this line", fontsize=14)
    doc.new_page().insert_text((72, 100), "john smith again", fontsize=14)
    doc.save(str(tmp_path / "letter.pdf"))
    return tmp_path / "letter.pdf"


def _all_text_both_libraries(path: Path) -> str:
    text = " ".join(page_texts(path))
    text += " ".join(p.extract_text() or "" for p in pypdf.PdfReader(str(path)).pages)
    return text.lower()


def test_redact_removes_text_for_good(tmp_path, letter) -> None:
    out = tmp_path / "r.pdf"
    assert pdfsuite.redact_text_pdf(letter, out, ["John Smith", "12345678"]) == 3
    text = _all_text_both_libraries(out)
    assert "john" not in text and "smith" not in text and "12345678" not in text
    assert "keep this line" in text and "secret" in text

    # A black box is drawn where the text was.
    with pymupdf.open(str(letter)) as doc:
        where = doc[0].search_for("12345678")[0]
    with pymupdf.open(str(out)) as doc:
        pix = doc[0].get_pixmap()
    centre = ((where.x0 + where.x1) / 2, (where.y0 + where.y1) / 2)
    assert pix.pixel(int(centre[0]), int(centre[1]))[:3] == (0, 0, 0)


def test_redact_ignores_case(tmp_path, letter) -> None:
    out = tmp_path / "r.pdf"
    assert pdfsuite.redact_text_pdf(letter, out, ["secret"]) == 1
    assert "secret" not in _all_text_both_libraries(out)


def test_redact_nothing_found_writes_nothing(tmp_path, letter, caplog) -> None:
    out = tmp_path / "r.pdf"
    assert pdfsuite.redact_text_pdf(letter, out, ["not there"]) is None
    assert "None of the text was found" in caplog.text
    assert not out.exists()
    assert pdfsuite.redact_text_pdf(letter, out, ["", "  "]) is None


def test_redact_warns_about_scanned_pages_and_metadata(tmp_path, caplog) -> None:
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 100), "Secret plan", fontsize=14)
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 20, 20), False)
    doc.new_page().insert_image(pymupdf.Rect(50, 50, 150, 150), pixmap=pix)  # image-only page
    doc.new_page()  # blank page: nothing to warn about
    doc.set_metadata({"title": "The secret plan"})
    doc.save(str(tmp_path / "in.pdf"))

    caplog.set_level(logging.WARNING)
    assert pdfsuite.redact_text_pdf(tmp_path / "in.pdf", tmp_path / "r.pdf", ["secret"]) == 1
    assert "no text layer (scanned?) were skipped: 2." in caplog.text
    assert "document details or bookmarks" in caplog.text


def test_redact_cli_and_menu(tmp_path, letter, monkeypatch) -> None:
    assert pdfsuite.main(["redact", "--in", str(letter), "--out", str(tmp_path / "c.pdf"), "--text", "john", "--text", "SECRET"]) == 0
    assert "john" not in _all_text_both_libraries(tmp_path / "c.pdf")
    assert pdfsuite.main(["redact", "--in", str(letter), "--out", str(tmp_path / "x.pdf"), "--text", "zzz"]) == 1

    feed_input(monkeypatch, ["26", str(letter), str(tmp_path / "m.pdf"), "smith | 12345678", "", "0"])
    assert pdfsuite.interactive_menu() == 0
    text = _all_text_both_libraries(tmp_path / "m.pdf")
    assert "smith" not in text and "12345678" not in text


# --- PDF/A --------------------------------------------------------------------


def _pdfa_id(path: Path) -> tuple[str | None, str | None]:
    pikepdf = pytest.importorskip("pikepdf")
    with pikepdf.open(str(path)) as pdf:
        meta = pdf.open_metadata()
        return meta.get("pdfaid:part"), meta.get("pdfaid:conformance")


def _scanned_pdf(path: Path) -> Path:
    from PIL import ImageDraw, ImageFont

    img = Image.new("RGB", (1600, 400), "white")
    ImageDraw.Draw(img).text((40, 120), "ARCHIVE TEST 77", fill="black", font=ImageFont.load_default(size=72))
    img.save(path, format="PDF", resolution=150)
    return path


@needs_ocr_tools
def test_pdfa_conversion(tmp_path) -> None:
    src = make_pdf(tmp_path / "in.pdf", 2)
    out = tmp_path / "a.pdf"
    assert pdfsuite.convert_to_pdfa(src, out)
    assert _pdfa_id(out) == ("2", "B")
    assert page_texts(out) == page_texts(src)


@needs_ocr_tools
def test_pdfa_ocr_option(tmp_path) -> None:
    scan = _scanned_pdf(tmp_path / "scan.pdf")
    plain, searchable = tmp_path / "plain.pdf", tmp_path / "ocr.pdf"
    assert pdfsuite.convert_to_pdfa(scan, plain)
    assert pdfsuite.convert_to_pdfa(scan, searchable, ocr=True)
    assert page_texts(plain) == [""]
    assert "ARCHIVE TEST 77" in page_texts(searchable)[0]
    assert _pdfa_id(searchable) == ("2", "B")


@needs_ocr_tools
def test_pdfa_encrypted_input(tmp_path, caplog) -> None:
    src = make_pdf(tmp_path / "in.pdf", 1)
    enc = tmp_path / "enc.pdf"
    assert pdfsuite.encrypt_pdf(src, enc, "pw") is not None
    assert not pdfsuite.convert_to_pdfa(enc, tmp_path / "a.pdf")
    assert "password-protected" in caplog.text


def test_pdfa_without_tesseract_explains(tmp_path, monkeypatch, caplog) -> None:
    pytest.importorskip("ocrmypdf")
    src = make_pdf(tmp_path / "in.pdf", 1)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    assert not pdfsuite.convert_to_pdfa(src, tmp_path / "a.pdf")
    assert "needs Tesseract and Ghostscript" in caplog.text


@needs_ocr_tools
def test_pdfa_cli_and_menu(tmp_path, monkeypatch) -> None:
    src = make_pdf(tmp_path / "in.pdf", 1)
    assert pdfsuite.main(["pdfa", "--in", str(src), "--out", str(tmp_path / "c.pdf")]) == 0
    assert _pdfa_id(tmp_path / "c.pdf") == ("2", "B")
    feed_input(monkeypatch, ["27", str(src), str(tmp_path / "m.pdf"), "n", "", "0"])
    assert pdfsuite.interactive_menu() == 0
    assert _pdfa_id(tmp_path / "m.pdf") == ("2", "B")
