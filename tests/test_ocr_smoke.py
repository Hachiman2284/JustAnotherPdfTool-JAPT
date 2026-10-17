from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# pdfsuite lives in ../src, which is not on sys.path for `python tests/...` or pytest.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pdfsuite import _find_ghostscript, _find_tesseract, configure_logging, images_to_pdf, ocr_pdf  # noqa: E402


def _make_test_jpg(path: Path) -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise RuntimeError("Missing dependency: Pillow (pip install pillow)") from exc

    img = Image.new("RGB", (1600, 500), "white")
    draw = ImageDraw.Draw(img)
    text = "OCR SMOKE TEST 123\nThe quick brown fox jumps over 13 lazy dogs."

    # Pillow's bundled font at a size Tesseract reads reliably (the bare
    # load_default() bitmap font is only ~10px tall).
    font = ImageFont.load_default(size=48)
    draw.multiline_text((40, 40), text, fill="black", font=font, spacing=10)

    img.save(path, format="JPEG", quality=95)


def _extract_pdf_text(pdf_path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise RuntimeError("Missing dependency: pypdf (pip install pypdf)") from exc

    reader = PdfReader(str(pdf_path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def main() -> int:
    configure_logging("INFO")
    with tempfile.TemporaryDirectory(prefix="ocr_smoke_") as tmp:
        return _run(Path(tmp))


def _run(out_dir: Path) -> int:
    jpg_path = out_dir / "page1.jpg"
    input_pdf = out_dir / "input.pdf"
    output_pdf = out_dir / "output_ocr.pdf"

    _make_test_jpg(jpg_path)

    if not images_to_pdf(out_dir, [jpg_path.name], output_pdf=input_pdf.name):
        print("FAILED: could not create input PDF")
        return 2

    ok = ocr_pdf(input_pdf, output_pdf, language="eng", force_ocr=True)
    if not ok:
        print("FAILED: ocr_pdf returned False")
        print("Tip: ocrmypdf needs Tesseract + Ghostscript available on PATH.")
        return 3

    extracted = _extract_pdf_text(output_pdf)
    print("--- Extracted text (first 300 chars) ---")
    print(extracted[:300].replace("\r", ""))

    # OCR text extraction can vary in spacing/punctuation; normalize for a stable check.
    normalized = "".join(ch for ch in extracted.upper() if ch.isalnum())
    if "OCRSMOKETEST123" not in normalized:
        print("FAILED: OCR text not found in extracted text")
        return 4

    print("OK: OCR smoke test passed")
    return 0


def test_ocr_smoke() -> None:
    """pytest entry point (the script entry point is main())."""
    import pytest

    if not (_find_tesseract() and _find_ghostscript()):
        pytest.skip("needs Tesseract and Ghostscript")
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
