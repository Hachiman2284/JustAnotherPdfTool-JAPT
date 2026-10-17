from __future__ import annotations

import builtins
import sys
from pathlib import Path

import pytest

# pdfsuite lives in ../src, which is not on sys.path for `python tests/...` or pytest.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pdfsuite  # noqa: E402

pymupdf = pytest.importorskip("pymupdf")
pypdf = pytest.importorskip("pypdf")


# --- helpers ----------------------------------------------------------------


def make_pdf(path: Path, pages: int = 3, label: str = "doc") -> Path:
    """Write a PDF whose page i (1-based) contains the text "<label> page <i>"."""
    doc = pymupdf.open()
    for i in range(1, pages + 1):
        doc.new_page().insert_text((72, 72), f"{label} page {i}", fontsize=14)
    doc.save(str(path))
    return path


def page_texts(path: Path) -> list[str]:
    with pymupdf.open(str(path)) as doc:
        return [" ".join(page.get_text("text").split()) for page in doc]


def page_labels(path: Path) -> list[str]:
    """The "<label> page <i>" marker of each page, in order."""
    labels = []
    for text in page_texts(path):
        words = text.split()
        i = words.index("page")
        labels.append(" ".join(words[i - 1 : i + 2]))
    return labels


def rotations(path: Path) -> list[int]:
    return [page.rotation for page in pypdf.PdfReader(str(path)).pages]


@pytest.fixture
def pdf3(tmp_path) -> Path:
    return make_pdf(tmp_path / "in.pdf", 3)


# --- page selection parsing -------------------------------------------------


@pytest.mark.parametrize(
    ("selection", "expected"),
    [
        ("1", [0]),
        ("1,3", [0, 2]),
        ("2-4", [1, 2, 3]),
        ("1, 3 - 4 ,6", [0, 2, 3, 5]),
        ("5,1-2", [4, 0, 1]),  # order as written
        ("1-3,2,3", [0, 1, 2]),  # duplicates removed
        ("10", [9]),
        ("1,,2", [0, 1]),  # empty parts ignored
    ],
)
def test_parse_page_selection(selection, expected) -> None:
    assert pdfsuite._parse_page_selection(selection, total_pages=10) == expected


@pytest.mark.parametrize("selection", ["", "  ", "0", "11", "3-1", "0-2", "5-11", "a", "1-x", "1.5", ",", "-1"])
def test_parse_page_selection_rejects(selection) -> None:
    with pytest.raises(ValueError):
        pdfsuite._parse_page_selection(selection, total_pages=10)


def test_parse_page_selection_clamp_end() -> None:
    assert pdfsuite._parse_page_selection("8-20", total_pages=10, clamp_end=True) == [7, 8, 9]
    with pytest.raises(ValueError):  # a start past the end is still an error
        pdfsuite._parse_page_selection("11-20", total_pages=10, clamp_end=True)


def test_parse_page_selection_needs_pages() -> None:
    with pytest.raises(ValueError):
        pdfsuite._parse_page_selection("1", total_pages=0)


def test_parse_order() -> None:
    assert pdfsuite._parse_order("3, 1,2") == [3, 1, 2]
    for bad in ("", " , ", "1,a"):
        with pytest.raises(ValueError):
            pdfsuite._parse_order(bad)


# --- merge ------------------------------------------------------------------


def test_merge_keeps_order(tmp_path) -> None:
    a = make_pdf(tmp_path / "a.pdf", 2, "A")
    b = make_pdf(tmp_path / "b.pdf", 1, "B")
    out = tmp_path / "sub" / "merged.pdf"
    assert pdfsuite.merge_pdfs([b, a], out)
    assert page_labels(out) == ["B page 1", "A page 1", "A page 2"]


def test_merge_missing_input_fails(tmp_path) -> None:
    a = make_pdf(tmp_path / "a.pdf", 1)
    out = tmp_path / "merged.pdf"
    assert not pdfsuite.merge_pdfs([a, tmp_path / "nope.pdf"], out)
    assert not out.exists()


# --- split ------------------------------------------------------------------


def test_split_single(tmp_path, pdf3) -> None:
    out_dir = tmp_path / "out"
    assert pdfsuite.split_pdf(pdf3, mode="single", output_dir=out_dir, prefix="x")
    files = sorted(p.name for p in out_dir.iterdir())
    assert files == ["x_page_0001.pdf", "x_page_0002.pdf", "x_page_0003.pdf"]
    assert page_labels(out_dir / "x_page_0002.pdf") == ["doc page 2"]


def test_split_range(tmp_path) -> None:
    src = make_pdf(tmp_path / "in.pdf", 6)
    assert pdfsuite.split_pdf(src, mode="range", page_range="5,2-3", output_dir=tmp_path)
    assert page_labels(tmp_path / "split_pages.pdf") == ["doc page 5", "doc page 2", "doc page 3"]


def test_split_range_default_clamps_on_short_pdf(tmp_path, pdf3) -> None:
    # The default range "1-10" must still work on a 3-page PDF.
    assert pdfsuite.split_pdf(pdf3, mode="range", output_dir=tmp_path)
    assert len(page_labels(tmp_path / "split_pages.pdf")) == 3


def test_split_chunk(tmp_path) -> None:
    src = make_pdf(tmp_path / "in.pdf", 5)
    out_dir = tmp_path / "chunks"
    assert pdfsuite.split_pdf(src, mode="chunk", chunk_size=2, output_dir=out_dir)
    chunks = sorted(out_dir.iterdir())
    assert [len(page_labels(c)) for c in chunks] == [2, 2, 1]
    assert page_labels(chunks[2]) == ["doc page 5"]


@pytest.mark.parametrize(
    "kwargs", [{"mode": "bogus"}, {"mode": "chunk", "chunk_size": 0}, {"mode": "range", "page_range": "9"}]
)
def test_split_bad_options_fail(tmp_path, pdf3, kwargs) -> None:
    assert not pdfsuite.split_pdf(pdf3, output_dir=tmp_path / "o", **kwargs)


# --- rotate / delete / reorder ----------------------------------------------


def test_rotate_all_pages(tmp_path, pdf3) -> None:
    out = tmp_path / "r.pdf"
    assert pdfsuite.rotate_pdf(pdf3, out, 90)
    assert rotations(out) == [90, 90, 90]


def test_rotate_selected_pages(tmp_path, pdf3) -> None:
    out = tmp_path / "r.pdf"
    assert pdfsuite.rotate_pdf(pdf3, out, 180, pages="1,3")
    assert rotations(out) == [180, 0, 180]
    assert page_labels(out) == ["doc page 1", "doc page 2", "doc page 3"]


@pytest.mark.parametrize(("angle", "pages"), [(45, None), (90, "4")])
def test_rotate_invalid_fails(tmp_path, pdf3, angle, pages) -> None:
    out = tmp_path / "r.pdf"
    assert not pdfsuite.rotate_pdf(pdf3, out, angle, pages=pages)
    assert not out.exists()


def test_delete_pages(tmp_path) -> None:
    src = make_pdf(tmp_path / "in.pdf", 5)
    out = tmp_path / "d.pdf"
    assert pdfsuite.delete_pages_pdf(src, out, "2,4-5")
    assert page_labels(out) == ["doc page 1", "doc page 3"]


@pytest.mark.parametrize("pages", ["1-3", "7", "x"])
def test_delete_pages_refuses_all_or_invalid(tmp_path, pdf3, pages) -> None:
    out = tmp_path / "d.pdf"
    assert not pdfsuite.delete_pages_pdf(pdf3, out, pages)
    assert not out.exists()


def test_reorder_pages(tmp_path, pdf3) -> None:
    out = tmp_path / "o.pdf"
    assert pdfsuite.reorder_pages_pdf(pdf3, out, [3, 1, 2])
    assert page_labels(out) == ["doc page 3", "doc page 1", "doc page 2"]


def test_reorder_can_duplicate_and_drop(tmp_path, pdf3) -> None:
    out = tmp_path / "o.pdf"
    assert pdfsuite.reorder_pages_pdf(pdf3, out, [2, 2])
    assert page_labels(out) == ["doc page 2", "doc page 2"]


@pytest.mark.parametrize("order", [[0, 1], [1, 4]])
def test_reorder_out_of_range_fails(tmp_path, pdf3, order) -> None:
    assert not pdfsuite.reorder_pages_pdf(pdf3, tmp_path / "o.pdf", order)


# --- adding text -------------------------------------------------------------


def test_header_footer_placeholders(tmp_path, pdf3) -> None:
    out = tmp_path / "hf.pdf"
    assert pdfsuite.add_header_footer_pdf(pdf3, out, header="Report {x}", footer="Page {page} of {pages}")
    texts = page_texts(out)
    for i, text in enumerate(texts, start=1):
        assert f"Page {i} of 3" in text
        assert "Report {x}" in text  # other braces kept literally


def test_header_footer_position(tmp_path, pdf3) -> None:
    out = tmp_path / "hf.pdf"
    assert pdfsuite.add_header_footer_pdf(pdf3, out, header="TOPTEXT", footer="BOTTOMTEXT", margin=40)
    with pymupdf.open(str(out)) as doc:
        page = doc[0]
        top = page.search_for("TOPTEXT")[0]
        bottom = page.search_for("BOTTOMTEXT")[0]
        assert top.y1 <= 45 and top.x0 >= 39
        assert bottom.y1 >= page.rect.height - 45


def test_watermark_on_every_page(tmp_path, pdf3) -> None:
    out = tmp_path / "w.pdf"
    assert pdfsuite.watermark_pdf(pdf3, out, "CONFIDENTIAL", rotate=30)
    texts = page_texts(out)
    assert all("CONFIDENTIAL" in t for t in texts)
    assert all("doc page" in t for t in texts)  # original content kept


def test_watermark_bad_opacity_fails(tmp_path, pdf3) -> None:
    assert not pdfsuite.watermark_pdf(pdf3, tmp_path / "w.pdf", "X", opacity=1.5)


# --- text, images, metadata --------------------------------------------------


def test_extract_text_default_path(tmp_path, pdf3) -> None:
    out = pdfsuite.extract_text_from_pdf(pdf3)
    assert out == pdf3.with_suffix(".txt")
    content = out.read_text(encoding="utf-8")
    assert all(f"doc page {i}" in content for i in (1, 2, 3))


def _pdf_with_image(path: Path) -> Path:
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 40, 30), False)
    pix.set_rect(pix.irect, (200, 30, 30))
    doc = pymupdf.open()
    for _ in range(2):
        doc.new_page().insert_image(pymupdf.Rect(50, 50, 250, 200), pixmap=pix)
    doc.save(str(path))
    return path


def test_extract_images(tmp_path) -> None:
    src = _pdf_with_image(tmp_path / "img.pdf")
    out_dir = tmp_path / "imgs"
    assert pdfsuite.extract_images_from_pdf(src, out_dir) == 2
    assert len(list(out_dir.iterdir())) == 2


def test_pdf_to_images(tmp_path, pdf3) -> None:
    out_dir = tmp_path / "pages"
    assert pdfsuite.pdf_to_images(pdf3, out_dir, dpi=72, fmt="png") == 3
    first = pymupdf.Pixmap(str(out_dir / "page_0001.png"))
    assert (first.width, first.height) == (595, 842)  # A4 at 72 dpi


def test_deocr_selected_pages(tmp_path, pdf3) -> None:
    out = tmp_path / "deocr.pdf"
    assert pdfsuite.deocr_selected_pages(pdf3, out, "2", dpi=72)
    texts = page_texts(out)
    assert texts[0] and texts[2]  # untouched pages keep their text
    assert texts[1] == ""  # converted page is image-only
    with pymupdf.open(str(out)) as doc:
        assert doc[1].get_images()


def test_metadata_set_keeps_other_keys(tmp_path, pdf3) -> None:
    first = tmp_path / "m1.pdf"
    second = tmp_path / "m2.pdf"
    assert pdfsuite.set_pdf_metadata(pdf3, first, {"/Title": "T", "/Author": "A"})
    assert pdfsuite.set_pdf_metadata(first, second, {"/Title": "New"})
    meta = pdfsuite.show_pdf_metadata(second)
    assert meta["/Title"] == "New"
    assert meta["/Author"] == "A"


def test_parse_metadata_json() -> None:
    assert pdfsuite._parse_metadata_json('{"/Title": "X", "/Pages": 3}') == {"/Title": "X", "/Pages": "3"}
    for bad in ("[1]", "{oops"):
        with pytest.raises(ValueError):
            pdfsuite._parse_metadata_json(bad)


def test_info_page_count_and_encryption(tmp_path, pdf3) -> None:
    enc = tmp_path / "enc.pdf"
    assert pdfsuite.pdf_page_count(pdf3) == 3
    assert pdfsuite.pdf_is_encrypted(pdf3) is False
    assert pdfsuite.encrypt_pdf(pdf3, enc, "pw") is not None
    assert pdfsuite.pdf_is_encrypted(enc) is True
    assert pdfsuite.pdf_page_count(enc) is None
    assert pdfsuite._show_pdf_info(enc) == 0
    assert pdfsuite._show_pdf_info(tmp_path / "missing.pdf") == 1


def test_compress_never_grows_and_stays_valid(tmp_path) -> None:
    src = _pdf_with_image(tmp_path / "img.pdf")
    out = tmp_path / "small.pdf"
    assert pdfsuite.compress_pdf(src, out)
    assert out.stat().st_size <= src.stat().st_size
    assert pdfsuite.pdf_page_count(out) == 2


def test_jpg_merge_natural_order(tmp_path) -> None:
    pil = pytest.importorskip("PIL.Image")
    pytest.importorskip("img2pdf")
    sizes = {"img1.jpg": (100, 50), "img2.jpeg": (100, 60), "img10.JPG": (100, 70)}
    for name, size in sizes.items():
        pil.new("RGB", size, "white").save(tmp_path / name, format="JPEG")
    (tmp_path / "notes.txt").write_text("not an image")

    assert pdfsuite.jpeg_to_pdf_merge(tmp_path, output_pdf="all.pdf")
    with pymupdf.open(str(tmp_path / "all.pdf")) as doc:
        # img2 must come before img10; page heights identify each image.
        heights = [round(p.rect.height / p.rect.width * 100) for p in doc]
    assert heights == [50, 60, 70]

    assert not pdfsuite.jpeg_to_pdf_merge(tmp_path, ["img1.jpg", "missing.jpg"], "x.pdf")
    assert not (tmp_path / "x.pdf").exists()


@pytest.mark.parametrize(
    "call",
    [
        lambda p, o: pdfsuite.rotate_pdf(p, o, 90),
        lambda p, o: pdfsuite.delete_pages_pdf(p, o, "1"),
        lambda p, o: pdfsuite.reorder_pages_pdf(p, o, [1]),
        lambda p, o: pdfsuite.watermark_pdf(p, o, "X"),
        lambda p, o: pdfsuite.add_header_footer_pdf(p, o, header="H"),
        lambda p, o: pdfsuite.compress_pdf(p, o),
        lambda p, o: pdfsuite.split_pdf(p, output_dir=o),
        lambda p, o: pdfsuite.extract_text_from_pdf(p, o),
    ],
)
def test_missing_input_fails_cleanly(tmp_path, call) -> None:
    result = call(tmp_path / "missing.pdf", tmp_path / "out.pdf")
    assert result in (False, None)
    assert not (tmp_path / "out.pdf").exists()


# --- batch ------------------------------------------------------------------


@pytest.fixture
def folder(tmp_path) -> Path:
    d = tmp_path / "batch"
    d.mkdir()
    make_pdf(d / "a.pdf", 2, "A")
    make_pdf(d / "b.pdf", 3, "B")
    (d / "skip.txt").write_text("not a pdf")
    return d


def test_batch_watermark(folder, tmp_path) -> None:
    out_dir = tmp_path / "out"
    assert pdfsuite.batch_process_folder(folder, operation="watermark", output_dir=out_dir, text="DRAFT") == (2, 2)
    assert sorted(p.name for p in out_dir.iterdir()) == ["a_watermarked.pdf", "b_watermarked.pdf"]
    assert all("DRAFT" in t for t in page_texts(out_dir / "b_watermarked.pdf"))


def test_batch_rotate_with_pages(folder) -> None:
    assert pdfsuite.batch_process_folder(folder, operation="rotate", angle=270, pages="1") == (2, 2)
    assert rotations(folder / "a_rotated.pdf") == [270, 0]
    assert rotations(folder / "b_rotated.pdf") == [270, 0, 0]


def test_batch_header_footer(folder) -> None:
    assert pdfsuite.batch_process_folder(folder, operation="header-footer", footer="{page}/{pages}") == (2, 2)
    texts = page_texts(folder / "b_header_footer.pdf")
    assert ["1/3" in texts[0], "2/3" in texts[1], "3/3" in texts[2]] == [True, True, True]


def test_batch_none_options_use_defaults(folder) -> None:
    # The CLI passes every option; None means "use the operation's default".
    assert (
        pdfsuite.batch_process_folder(
            folder, operation="watermark", text="X", fontsize=None, rotate=None, opacity=None
        )
        == (2, 2)
    )


def test_batch_existing_operations_still_work(folder) -> None:
    assert pdfsuite.batch_process_folder(folder, operation="extract-text", glob_pattern="a*.pdf") == (1, 1)
    assert pdfsuite.batch_process_folder(folder, operation="compress") == (2, 2)
    assert "A page 2" in (folder / "a.txt").read_text(encoding="utf-8")
    assert (folder / "b_compressed.pdf").exists()


def test_batch_partial_failure_counts_successes(folder, caplog) -> None:
    # Page 3 exists only in b.pdf, so a.pdf fails and b.pdf succeeds.
    result = pdfsuite.batch_process_folder(folder, operation="rotate", angle=90, pages="3")
    assert result == (1, 2)
    assert not result.all_succeeded
    assert not (folder / "a_rotated.pdf").exists()
    assert (folder / "b_rotated.pdf").exists()
    assert "1 of 2 files failed: a.pdf" in caplog.text


def test_batch_result_all_succeeded() -> None:
    assert pdfsuite.BatchResult(2, 2).all_succeeded
    assert not pdfsuite.BatchResult(1, 2).all_succeeded
    assert not pdfsuite.BatchResult(0, 0).all_succeeded


def test_batch_partial_failure_reported_as_failed(folder, monkeypatch, capsys) -> None:
    # CLI: exit code 1 when any file fails.
    assert pdfsuite.main(["batch", "--folder", str(folder), "--op", "rotate", "--angle", "90", "--pages", "3"]) == 1
    assert pdfsuite.main(["batch", "--folder", str(folder), "--op", "rotate", "--angle", "90", "--pages", "1"]) == 0

    # Menu: shows "Failed." instead of "Done.".
    answers = iter(["20", str(folder), "rotate", "", str(folder / "out"), "90", "3", "", "0"])
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(answers))
    assert pdfsuite.interactive_menu() == 0
    out = capsys.readouterr().out
    assert "Failed. See the messages above." in out
    assert "Done." not in out


@pytest.mark.parametrize(
    "kwargs",
    [
        {"operation": "bogus"},
        {"operation": "watermark"},
        {"operation": "watermark", "text": ""},
        {"operation": "rotate"},
        {"operation": "rotate", "angle": 45},
        {"operation": "header-footer"},
        {"operation": "compress", "glob_pattern": "*.nothing"},
    ],
)
def test_batch_rejects_bad_requests_before_writing(folder, kwargs) -> None:
    before = sorted(folder.iterdir())
    assert pdfsuite.batch_process_folder(folder, **kwargs) == (0, 0)
    assert sorted(folder.iterdir()) == before


def test_batch_missing_folder(tmp_path) -> None:
    assert pdfsuite.batch_process_folder(tmp_path / "nope", operation="compress") == (0, 0)


def test_batch_cli(folder, tmp_path) -> None:
    out_dir = tmp_path / "cli"
    rc = pdfsuite.main(
        ["batch", "--folder", str(folder), "--op", "watermark", "--text", "CLI", "--opacity", "0.3", "--out-dir", str(out_dir)]
    )
    assert rc == 0
    assert len(list(out_dir.iterdir())) == 2
    assert pdfsuite.main(["batch", "--folder", str(folder), "--op", "rotate", "--angle", "45"]) == 1
    with pytest.raises(SystemExit):
        pdfsuite.main(["batch", "--folder", str(folder), "--op", "bogus"])


def test_batch_menu_asks_operation_questions(folder, monkeypatch) -> None:
    answers = iter(["20", str(folder), "rotate", "", "", "180", "2", "", "0"])
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(answers))
    assert pdfsuite.interactive_menu() == 0
    assert rotations(folder / "a_rotated.pdf") == [0, 180]
