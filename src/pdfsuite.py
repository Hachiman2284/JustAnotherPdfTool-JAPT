import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable, Sequence


logger = logging.getLogger("pdfsuite")


def configure_logging(level: str = "INFO") -> None:
    """Configure the module logger.

    Args:
        level: Logging level name (e.g. "DEBUG", "INFO", "WARNING", "ERROR").
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def _ensure_parent_dir(path: Path) -> None:
    """Create the parent directory for a file path if missing."""
    path.parent.mkdir(parents=True, exist_ok=True)


def _as_path(value: str | Path) -> Path:
    """Convert a string/Path input to a Path."""
    return value if isinstance(value, Path) else Path(value)


def _bytes_like_to_str(value: str | bytes | memoryview) -> str:
    """Convert bytes-like values to a UTF-8 string."""
    if isinstance(value, str):
        return value
    return bytes(value).decode("utf-8", errors="ignore")


def pdf_to_docx(input_pdf: str | Path, output_docx: str | Path) -> bool:
    """Convert a PDF file to a DOCX file.

    Args:
        input_pdf: Path to the input PDF.
        output_docx: Path to the output DOCX.

    Returns:
        True if successful, otherwise False.

    Notes:
        Requires the third-party package `pdf2docx`.
    """
    input_pdf = _as_path(input_pdf)
    output_docx = _as_path(output_docx)
    if not input_pdf.exists():
        logger.error("Input PDF not found: %s", input_pdf)
        return False

    try:
        from pdf2docx import Converter
    except ModuleNotFoundError:
        logger.error("Missing dependency: pdf2docx (install with `pip install pdf2docx`)")
        return False

    try:
        _ensure_parent_dir(output_docx)
        cv = Converter(str(input_pdf))
        cv.convert(str(output_docx))
        cv.close()
        logger.info("Converted PDF -> DOCX: %s", output_docx)
        return True
    except Exception as exc:
        logger.error("PDF->DOCX failed: %s", exc)
        return False


def docx_to_pdf(input_docx: str | Path, output_pdf: str | Path) -> bool:
    """Convert a DOCX file to PDF.

    This tries the `docx2pdf` Python package first (recommended on Windows
    where it uses Microsoft Word). If unavailable, it falls back to a
    headless LibreOffice (`soffice`) conversion.
    """
    input_docx = _as_path(input_docx)
    output_pdf = _as_path(output_pdf)
    if not input_docx.exists():
        logger.error("Input DOCX not found: %s", input_docx)
        return False

    # Try docx2pdf first
    try:
        from docx2pdf import convert

        _ensure_parent_dir(output_pdf)
        try:
            # docx2pdf accepts (input, output) where output may be a folder
            convert(str(input_docx), str(output_pdf))
            logger.info("Converted DOCX -> PDF via docx2pdf: %s", output_pdf)
            return True
        except Exception as exc:
            logger.warning("docx2pdf conversion failed: %s", exc)
    except ModuleNotFoundError:
        logger.debug("docx2pdf not available, will try LibreOffice")

    # Fallback: LibreOffice/soffice (headless). Create output in a temporary
    # directory and move the resulting file to the requested path.
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        logger.error(
            "No conversion backend available. Install `docx2pdf` or LibreOffice (soffice)."
        )
        return False

    out_dir = None
    try:
        out_dir = Path(tempfile.mkdtemp())
        cmd = [
            soffice,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(out_dir),
            str(input_docx),
        ]
        completed = subprocess.run(cmd, capture_output=True, text=True)
        if completed.returncode != 0:
            logger.error("LibreOffice conversion failed: %s", (completed.stderr or completed.stdout))
            return False

        produced = out_dir / (input_docx.stem + ".pdf")
        if not produced.exists():
            logger.error("LibreOffice did not produce expected PDF: %s", produced)
            return False

        _ensure_parent_dir(output_pdf)
        shutil.move(str(produced), str(output_pdf))
        logger.info("Converted DOCX -> PDF via LibreOffice: %s", output_pdf)
        return True
    except Exception as exc:
        logger.error("DOCX->PDF conversion failed: %s", exc)
        return False
    finally:
        if out_dir is not None:
            try:
                if out_dir.exists():
                    shutil.rmtree(str(out_dir))
            except Exception:
                pass


def ocr_pdf(
    input_pdf: str | Path,
    output_pdf: str | Path,
    language: str = "eng",
    *,
    deskew: bool = False,
    rotate_pages: bool = False,
    remove_background: bool = False,
    optimize: int = 1,
    force_ocr: bool = False,
    skip_text: bool = False,
) -> bool:
    """Run OCR on a scanned PDF to create a searchable PDF.

    Args:
        input_pdf: Path to input PDF.
        output_pdf: Path to output searchable PDF.
        language: OCR language code (e.g. "eng").
        deskew: Deskew pages.
        rotate_pages: Auto-rotate pages.
        remove_background: Remove background.
        optimize: Optimization level (0-3) (ocrmypdf).
        force_ocr: OCR even if text exists.
        skip_text: Skip pages that already have text.

    Returns:
        True if successful, otherwise False.

    Notes:
        Requires the third-party package `ocrmypdf`.
    """
    input_pdf = _as_path(input_pdf)
    output_pdf = _as_path(output_pdf)
    if not input_pdf.exists():
        logger.error("Input PDF not found: %s", input_pdf)
        return False

    try:
        import ocrmypdf
        from ocrmypdf.exceptions import PriorOcrFoundError
    except ModuleNotFoundError:
        logger.error("Missing dependency: ocrmypdf (install with `pip install ocrmypdf`)")
        return False

    try:
        _ensure_parent_dir(output_pdf)
        logger.info("Starting OCR: %s", input_pdf)
        ocrmypdf.ocr(
            str(input_pdf),
            str(output_pdf),
            language=language,
            output_type="pdf",
            deskew=deskew,
            rotate_pages=rotate_pages,
            remove_background=remove_background,
            optimize=optimize,
            force_ocr=force_ocr,
            skip_text=skip_text,
        )
        logger.info("OCR complete: %s", output_pdf)
        return True
    except PriorOcrFoundError:
        logger.error("Prior OCR/text detected. Use --force-ocr to override.")
        return False
    except Exception as exc:
        logger.error("OCR failed: %s", exc)
        return False


def merge_pdfs(pdf_paths: Sequence[str | Path], output_pdf: str | Path) -> bool:
    """Merge multiple PDFs into one.

    Args:
        pdf_paths: PDFs to merge, in order.
        output_pdf: Path to merged output PDF.

    Returns:
        True if successful, otherwise False.
    """
    output_pdf = _as_path(output_pdf)
    resolved = [_as_path(p) for p in pdf_paths]
    missing = [p for p in resolved if not p.exists()]
    if missing:
        logger.error("Missing input PDFs: %s", ", ".join(str(p) for p in missing))
        return False

    try:
        from pypdf import PdfReader, PdfWriter
    except ModuleNotFoundError:
        logger.error("Missing dependency: pypdf (install with `pip install pypdf`)")
        return False

    try:
        writer = PdfWriter()
        for path in resolved:
            reader = PdfReader(str(path))
            for page in reader.pages:
                writer.add_page(page)

        _ensure_parent_dir(output_pdf)
        with open(output_pdf, "wb") as f:
            writer.write(f)
        logger.info("Merged %d PDFs -> %s", len(resolved), output_pdf)
        return True
    except Exception as exc:
        logger.error("Merge failed: %s", exc)
        return False


def jpeg_to_pdf_merge(
    image_folder: str | Path,
    jpg_files: Sequence[str] | None = None,
    output_pdf: str | Path = "merged_output.pdf",
) -> bool:
    """Convert JPG/JPEG images into a single multi-page PDF.

    Args:
        image_folder: Folder containing images.
        jpg_files: Optional list of filenames (order is preserved). If None, uses all .jpg/.jpeg in folder.
        output_pdf: Output PDF path. If relative, it is created inside image_folder.

    Returns:
        True if successful, otherwise False.

    Notes:
        Requires the third-party package `Pillow`.
    """
    image_folder = _as_path(image_folder)
    output_pdf = _as_path(output_pdf)
    if not output_pdf.is_absolute():
        output_pdf = image_folder / output_pdf

    if not image_folder.exists():
        logger.error("Image folder not found: %s", image_folder)
        return False

    try:
        from PIL import Image
    except ModuleNotFoundError:
        logger.error("Missing dependency: Pillow (install with `pip install pillow`)")
        return False

    try:
        if jpg_files is None:
            jpg_files = sorted(
                [
                    p.name
                    for p in image_folder.iterdir()
                    if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg"}
                ]
            )

        if not jpg_files:
            logger.error("No JPG/JPEG files found in: %s", image_folder)
            return False

        images = []
        for filename in jpg_files:
            img_path = image_folder / filename
            if not img_path.exists():
                logger.error("Image not found: %s", img_path)
                continue
            img = Image.open(img_path)
            if img.mode != "RGB":
                img = img.convert("RGB")
            images.append(img)
            logger.info("Added image: %s", img_path.name)

        if not images:
            logger.error("No valid images to convert.")
            return False

        _ensure_parent_dir(output_pdf)
        images[0].save(str(output_pdf), save_all=True, append_images=images[1:])
        logger.info("Created PDF: %s (%d pages)", output_pdf, len(images))

        for img in images:
            try:
                img.close()
            except Exception:
                pass

        return True
    except Exception as exc:
        logger.error("JPG->PDF merge failed: %s", exc)
        return False


def split_pdf(
    input_pdf: str | Path,
    *,
    mode: str = "single",
    page_range: str = "1-10",
    chunk_size: int = 1,
    output_dir: str | Path = ".",
    prefix: str = "",
) -> bool:
    """Split a PDF into smaller PDFs.

    Args:
        input_pdf: Input PDF.
        mode: One of: "single", "range", "chunk".
        page_range: Page range string (used for mode="range").
        chunk_size: Chunk size (used for mode="chunk").
        output_dir: Directory for output files.
        prefix: Optional filename prefix.

    Returns:
        True if successful, otherwise False.
    """
    input_pdf = _as_path(input_pdf)
    output_dir = _as_path(output_dir)
    if not input_pdf.exists():
        logger.error("Input PDF not found: %s", input_pdf)
        return False

    try:
        from pypdf import PdfReader, PdfWriter
    except ModuleNotFoundError:
        logger.error("Missing dependency: pypdf (install with `pip install pypdf`)")
        return False

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        reader = PdfReader(str(input_pdf))
        total = len(reader.pages)
        prefix_part = f"{prefix}_" if prefix else ""

        if mode == "single":
            for i, page in enumerate(reader.pages, start=1):
                writer = PdfWriter()
                writer.add_page(page)
                out = output_dir / f"{prefix_part}page_{i:04d}.pdf"
                with open(out, "wb") as f:
                    writer.write(f)
            logger.info("Split into %d single-page PDFs in %s", total, output_dir)
            return True

        if mode == "range":
            writer = PdfWriter()
            indices = _parse_page_selection(page_range, total_pages=total)

            for page_num in indices:
                writer.add_page(reader.pages[page_num])

            out = output_dir / f"{prefix_part}split_pages.pdf"
            with open(out, "wb") as f:
                writer.write(f)
            logger.info("Wrote selected pages %s -> %s", page_range, out)
            return True

        if mode == "chunk":
            if chunk_size <= 0:
                logger.error("chunk_size must be > 0")
                return False
            chunk_idx = 0
            for index in range(0, total, chunk_size):
                chunk_idx += 1
                writer = PdfWriter()
                for page in reader.pages[index : index + chunk_size]:
                    writer.add_page(page)
                out = output_dir / f"{prefix_part}chunk_{chunk_idx:04d}.pdf"
                with open(out, "wb") as f:
                    writer.write(f)
            logger.info("Split into %d chunks in %s", chunk_idx, output_dir)
            return True

        logger.error("Unknown split mode: %s", mode)
        return False
    except Exception as exc:
        logger.error("Split failed: %s", exc)
        return False


def compress_pdf(input_pdf: str | Path, output_pdf: str | Path) -> bool:
    """Compress a PDF file.

    This function tries multiple strategies:
    1) Ghostscript (if available): best size reduction, but can be lossy
       because it may downsample/recompress images.
    2) PyMuPDF (if available): lossless cleanup/deflate/garbage collection.
    3) pikepdf (if available): qpdf-style stream/object compression.

    Args:
        input_pdf: Input PDF.
        output_pdf: Output PDF.

    Returns:
        True if successful, otherwise False.

    Notes:
        If your PDF is already optimized (most text PDFs are), "compression" may
        only shave off a small amount. Big reductions typically require image
        downsampling/re-encoding (lossy) via Ghostscript.
    """
    input_pdf = _as_path(input_pdf)
    output_pdf = _as_path(output_pdf)
    if not input_pdf.exists():
        logger.error("Input PDF not found: %s", input_pdf)
        return False

    def _size(path: Path) -> int:
        try:
            return path.stat().st_size
        except OSError:
            return -1

    def _log_sizes(method: str) -> None:
        before = _size(input_pdf)
        after = _size(output_pdf)
        if before > 0 and after > 0:
            delta = before - after
            pct = (delta / before) * 100
            logger.info(
                "Compressed via %s: %s -> %s (saved %d bytes, %.2f%%)",
                method,
                before,
                after,
                delta,
                pct,
            )
        else:
            logger.info("Compressed via %s -> %s", method, output_pdf)

    def _find_ghostscript() -> str | None:
        # On Windows the common console executables are gswin64c/gswin32c.
        for exe in ("gswin64c", "gswin32c", "gs"):
            resolved = shutil.which(exe)
            if resolved:
                return resolved
        return None

    def _run_ghostscript(profile: str, out_path: Path) -> bool:
        gs = _find_ghostscript()
        if not gs:
            return False

        allowed = {"screen", "ebook", "printer", "prepress", "default"}
        if profile not in allowed:
            logger.warning("Unknown Ghostscript profile '%s' (using 'ebook')", profile)
            profile = "ebook"

        cmd = [
            gs,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS=/{profile}",
            "-dNOPAUSE",
            "-dBATCH",
            "-dQUIET",
            # Avoid surprising page rotations.
            "-dAutoRotatePages=/None",
            # Best-effort reductions that are generally safe.
            "-dDetectDuplicateImages=true",
            "-dCompressFonts=true",
            "-dSubsetFonts=true",
            f"-sOutputFile={str(out_path)}",
            str(input_pdf),
        ]

        try:
            completed = subprocess.run(cmd, capture_output=True, text=True)
            if completed.returncode != 0:
                stderr = (completed.stderr or "").strip()
                logger.warning("Ghostscript failed (%s, rc=%s): %s", profile, completed.returncode, stderr)
                return False
            return True
        except Exception as exc:
            logger.warning("Ghostscript failed (%s): %s", profile, exc)
            return False

    def _compress_with_ghostscript_auto() -> bool:
        gs = _find_ghostscript()
        if not gs:
            return False

        _ensure_parent_dir(output_pdf)

        def _mktemp_pdf() -> Path:
            fd, name = tempfile.mkstemp(suffix=".pdf")
            try:
                os.close(fd)
            except Exception:
                pass
            return Path(name)

        tmp_ebook = _mktemp_pdf()
        tmp_screen = _mktemp_pdf()
        try:
            if not _run_ghostscript("ebook", tmp_ebook):
                return False

            before = _size(input_pdf)
            ebook_size = _size(tmp_ebook)

            # If /ebook barely helps, try /screen and keep the smaller of the two.
            try_screen = False
            if before > 0 and ebook_size > 0:
                saved_pct = ((before - ebook_size) / before) * 100
                if saved_pct < 2.0:
                    try_screen = True

            best_tmp = tmp_ebook
            best_profile = "ebook"

            if try_screen and _run_ghostscript("screen", tmp_screen):
                screen_size = _size(tmp_screen)
                if screen_size > 0 and (ebook_size <= 0 or screen_size < ebook_size):
                    best_tmp = tmp_screen
                    best_profile = "screen"

            # Move best result into place.
            try:
                if output_pdf.exists():
                    output_pdf.unlink()
            except Exception:
                pass
            shutil.move(str(best_tmp), str(output_pdf))
            _log_sizes(f"ghostscript/{best_profile}")
            return True
        finally:
            for p in (tmp_ebook, tmp_screen):
                try:
                    if p.exists():
                        p.unlink()
                except Exception:
                    pass

    def _pymupdf_save_with_kwargs(doc: object, path: Path, kwargs: dict) -> None:
        # PyMuPDF kwargs vary by version; iteratively drop unsupported kwargs.
        save_fn = getattr(doc, "save")
        current = dict(kwargs)
        while True:
            try:
                save_fn(str(path), **current)
                return
            except TypeError as exc:
                msg = str(exc)
                m = re.search(r"unexpected keyword argument '([^']+)'", msg)
                if not m:
                    raise
                bad = m.group(1)
                if bad in current:
                    current.pop(bad)
                    continue
                raise

    def _compress_with_pymupdf_lossless() -> bool:
        try:
            import pymupdf
        except ModuleNotFoundError:
            return False

        try:
            _ensure_parent_dir(output_pdf)
            doc = pymupdf.open(str(input_pdf))
            # garbage/clean/deflate are generally safe and can remove unused objects.
            kwargs = {
                "garbage": 4,
                "clean": True,
                "deflate": True,
                # If supported by the installed version, these can reduce size further.
                "deflate_images": True,
                "deflate_fonts": True,
                "linear": True,
            }
            _pymupdf_save_with_kwargs(doc, output_pdf, kwargs)
            _log_sizes("pymupdf(lossless)")
            return True
        except Exception as exc:
            logger.warning("PyMuPDF compression failed: %s", exc)
            return False

    def _pikepdf_save_with_kwargs(pdf: object, path: Path, kwargs: dict) -> None:
        save_fn = getattr(pdf, "save")
        current = dict(kwargs)
        while True:
            try:
                save_fn(str(path), **current)
                return
            except TypeError as exc:
                msg = str(exc)
                m = re.search(r"unexpected keyword argument '([^']+)'", msg)
                if not m:
                    raise
                bad = m.group(1)
                if bad in current:
                    current.pop(bad)
                    continue
                raise

    def _compress_with_pikepdf_lossless() -> bool:
        try:
            import pikepdf as pike
        except ModuleNotFoundError:
            return False

        try:
            _ensure_parent_dir(output_pdf)
            with pike.open(str(input_pdf)) as pdf:
                kwargs = {
                    "compress_streams": True,
                    "object_stream_mode": pike.ObjectStreamMode.generate,
                    # Some versions support linearize; keep best-effort.
                    "linearize": True,
                }
                _pikepdf_save_with_kwargs(pdf, output_pdf, kwargs)
            _log_sizes("pikepdf(lossless)")
            return True
        except Exception as exc:
            logger.warning("pikepdf compression failed: %s", exc)
            return False

    # 1) Prefer Ghostscript for substantial reductions (especially scanned/image PDFs).
    #    'ebook' is a reasonable default tradeoff (smaller than 'printer', better than 'screen').
    if _compress_with_ghostscript_auto():
        return True

    # 2) Lossless fallbacks.
    if _compress_with_pymupdf_lossless():
        return True
    if _compress_with_pikepdf_lossless():
        return True

    logger.error(
        "No available compressor. Install Ghostscript or `pymupdf` or `pikepdf`. "
        "(Ghostscript gives the biggest size reductions.)"
    )
    return False


def extract_text_from_pdf(input_pdf: str | Path, output_txt: str | Path | None = None) -> Path | None:
    """Extract text from a PDF and write to a UTF-8 .txt file.

    Args:
        input_pdf: Input PDF.
        output_txt: Output .txt path. If None, uses input filename with .txt suffix.

    Returns:
        The output path on success; otherwise None.

    Notes:
        Requires the third-party package `pymupdf`.
    """
    input_pdf = _as_path(input_pdf)
    if not input_pdf.exists():
        logger.error("Input PDF not found: %s", input_pdf)
        return None

    try:
        import pymupdf
    except ModuleNotFoundError:
        logger.error("Missing dependency: pymupdf (install with `pip install pymupdf`)")
        return None

    try:
        doc = pymupdf.open(str(input_pdf))
        output_txt = _as_path(output_txt) if output_txt is not None else input_pdf.with_suffix(".txt")
        _ensure_parent_dir(output_txt)

        with open(output_txt, "w", encoding="utf-8") as f:
            for page in doc:
                text = page.get_text("text")
                if not isinstance(text, str):
                    text = str(text)
                f.write(text)

        logger.info("Extracted text -> %s", output_txt)
        return output_txt
    except Exception as exc:
        logger.error("Text extraction failed: %s", exc)
        return None


def pdf_page_count(input_pdf: str | Path) -> int | None:
    """Return the number of pages in a PDF."""
    input_pdf = _as_path(input_pdf)
    if not input_pdf.exists():
        logger.error("Input PDF not found: %s", input_pdf)
        return None
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(input_pdf))
        return len(reader.pages)
    except Exception as exc:
        logger.error("Failed to read PDF: %s", exc)
        return None


def pdf_is_encrypted(input_pdf: str | Path) -> bool | None:
    """Return whether a PDF is encrypted."""
    input_pdf = _as_path(input_pdf)
    if not input_pdf.exists():
        logger.error("Input PDF not found: %s", input_pdf)
        return None
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(input_pdf))
        return bool(reader.is_encrypted)
    except Exception as exc:
        logger.error("Failed to read PDF: %s", exc)
        return None


def encrypt_pdf(input_pdf: str | Path, output_pdf: str | Path, password: str | bytes | memoryview) -> Path | None:
    """Encrypt a PDF with a user password.

    Args:
        input_pdf: Input PDF.
        output_pdf: Output PDF.
        password: Password (string or bytes-like).

    Returns:
        Output path on success, otherwise None.
    """
    input_pdf = _as_path(input_pdf)
    output_pdf = _as_path(output_pdf)
    if not input_pdf.exists():
        logger.error("Input PDF not found: %s", input_pdf)
        return None

    try:
        from pypdf import PdfReader, PdfWriter
    except ModuleNotFoundError:
        logger.error("Missing dependency: pypdf (install with `pip install pypdf`)")
        return None

    try:
        reader = PdfReader(str(input_pdf))
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        user_password = _bytes_like_to_str(password)
        writer.encrypt(user_password)

        _ensure_parent_dir(output_pdf)
        with open(output_pdf, "wb") as f:
            writer.write(f)
        logger.info("Encrypted PDF -> %s", output_pdf)
        return output_pdf
    except Exception as exc:
        logger.error("Encrypt failed: %s", exc)
        return None


def decrypt_pdf(
    input_pdf: str | Path,
    output_pdf: str | Path,
    password: str | bytes | memoryview,
) -> Path | None:
    """Decrypt an encrypted PDF and write an unencrypted copy.

    Args:
        input_pdf: Input PDF.
        output_pdf: Output PDF.
        password: Password (string or bytes-like).

    Returns:
        Output path on success, otherwise None.
    """
    input_pdf = _as_path(input_pdf)
    output_pdf = _as_path(output_pdf)
    if not input_pdf.exists():
        logger.error("Input PDF not found: %s", input_pdf)
        return None

    try:
        from pypdf import PdfReader, PdfWriter
    except ModuleNotFoundError:
        logger.error("Missing dependency: pypdf (install with `pip install pypdf`)")
        return None

    try:
        reader = PdfReader(str(input_pdf))
        if reader.is_encrypted:
            ok = reader.decrypt(_bytes_like_to_str(password))
            if not ok:
                logger.error("Incorrect password or unable to decrypt.")
                return None

        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        _ensure_parent_dir(output_pdf)
        with open(output_pdf, "wb") as f:
            writer.write(f)

        logger.info("Decrypted PDF -> %s", output_pdf)
        return output_pdf
    except Exception as exc:
        logger.error("Decrypt failed: %s", exc)
        return None


def rotate_pdf(input_pdf: str | Path, output_pdf: str | Path, angle: int, pages: str | None = None) -> bool:
    """Rotate pages in a PDF.

    Args:
        input_pdf: Input PDF.
        output_pdf: Output PDF.
        angle: Rotation angle in degrees (typically 90/180/270).
        pages: Optional page selection string (1-based), e.g. "1-3,6".

    Returns:
        True if successful, otherwise False.
    """
    input_pdf = _as_path(input_pdf)
    output_pdf = _as_path(output_pdf)
    if not input_pdf.exists():
        logger.error("Input PDF not found: %s", input_pdf)
        return False

    try:
        from pypdf import PdfReader, PdfWriter
    except ModuleNotFoundError:
        logger.error("Missing dependency: pypdf (install with `pip install pypdf`)")
        return False

    try:
        reader = PdfReader(str(input_pdf))
        writer = PdfWriter()
        selected: set[int] | None = None
        if pages:
            selected = set(_parse_page_selection(pages, total_pages=len(reader.pages)))

        for idx, page in enumerate(reader.pages):
            if selected is None or idx in selected:
                if hasattr(page, "rotate"):
                    page.rotate(angle)
                else:
                    rotate_clockwise = getattr(page, "rotate_clockwise", None)
                    if callable(rotate_clockwise):
                        rotate_clockwise(angle)
            writer.add_page(page)

        _ensure_parent_dir(output_pdf)
        with open(output_pdf, "wb") as f:
            writer.write(f)
        logger.info("Rotated PDF -> %s", output_pdf)
        return True
    except Exception as exc:
        logger.error("Rotate failed: %s", exc)
        return False


def delete_pages_pdf(input_pdf: str | Path, output_pdf: str | Path, pages: str) -> bool:
    """Delete selected pages from a PDF.

    Args:
        input_pdf: Input PDF.
        output_pdf: Output PDF.
        pages: Page selection string (1-based), e.g. "1-3,6".

    Returns:
        True if successful, otherwise False.
    """
    input_pdf = _as_path(input_pdf)
    output_pdf = _as_path(output_pdf)
    if not input_pdf.exists():
        logger.error("Input PDF not found: %s", input_pdf)
        return False

    try:
        from pypdf import PdfReader, PdfWriter
    except ModuleNotFoundError:
        logger.error("Missing dependency: pypdf (install with `pip install pypdf`)")
        return False

    try:
        reader = PdfReader(str(input_pdf))
        to_delete = set(_parse_page_selection(pages, total_pages=len(reader.pages)))

        writer = PdfWriter()
        kept = 0
        for idx, page in enumerate(reader.pages):
            if idx not in to_delete:
                writer.add_page(page)
                kept += 1

        _ensure_parent_dir(output_pdf)
        with open(output_pdf, "wb") as f:
            writer.write(f)
        logger.info("Deleted pages (%s). Kept %d pages -> %s", pages, kept, output_pdf)
        return True
    except Exception as exc:
        logger.error("Delete pages failed: %s", exc)
        return False


def reorder_pages_pdf(input_pdf: str | Path, output_pdf: str | Path, order: Sequence[int]) -> bool:
    """Reorder pages of a PDF.

    Args:
        input_pdf: Input PDF.
        output_pdf: Output PDF.
        order: 1-based page order list (e.g. [2,1,3]).

    Returns:
        True if successful, otherwise False.
    """
    input_pdf = _as_path(input_pdf)
    output_pdf = _as_path(output_pdf)
    if not input_pdf.exists():
        logger.error("Input PDF not found: %s", input_pdf)
        return False

    try:
        from pypdf import PdfReader, PdfWriter
    except ModuleNotFoundError:
        logger.error("Missing dependency: pypdf (install with `pip install pypdf`)")
        return False

    try:
        reader = PdfReader(str(input_pdf))
        total = len(reader.pages)
        indices = [i - 1 for i in order]
        if any(i < 0 or i >= total for i in indices):
            logger.error("Order contains out-of-range page numbers (1..%d)", total)
            return False

        writer = PdfWriter()
        for idx in indices:
            writer.add_page(reader.pages[idx])

        _ensure_parent_dir(output_pdf)
        with open(output_pdf, "wb") as f:
            writer.write(f)
        logger.info("Reordered PDF -> %s", output_pdf)
        return True
    except Exception as exc:
        logger.error("Reorder failed: %s", exc)
        return False


def add_header_footer_pdf(
    input_pdf: str | Path,
    output_pdf: str | Path,
    *,
    header: str | None = None,
    footer: str | None = None,
    margin: float = 36,
    fontsize: float = 10,
) -> bool:
    """Add simple header/footer text to each page using PyMuPDF.

    Args:
        input_pdf: Input PDF.
        output_pdf: Output PDF.
        header: Header text (optional). Supports "{page}" and "{pages}" placeholders.
        footer: Footer text (optional). Supports "{page}" and "{pages}" placeholders.
        margin: Distance from top/bottom in points.
        fontsize: Font size.

    Returns:
        True if successful, otherwise False.

    Notes:
        Requires the third-party package `pymupdf`.
    """
    input_pdf = _as_path(input_pdf)
    output_pdf = _as_path(output_pdf)
    if not input_pdf.exists():
        logger.error("Input PDF not found: %s", input_pdf)
        return False

    try:
        import pymupdf
    except ModuleNotFoundError:
        logger.error("Missing dependency: pymupdf (install with `pip install pymupdf`)")
        return False

    try:
        doc = pymupdf.open(str(input_pdf))
        pages = int(doc.page_count)
        for page_no in range(1, pages + 1):
            page = doc.load_page(page_no - 1)
            rect = page.rect
            if header:
                page.insert_text(
                    (margin, margin),
                    header.format(page=page_no, pages=pages),
                    fontsize=fontsize,
                )
            if footer:
                page.insert_text(
                    (margin, rect.height - margin),
                    footer.format(page=page_no, pages=pages),
                    fontsize=fontsize,
                )

        _ensure_parent_dir(output_pdf)
        doc.save(str(output_pdf))
        logger.info("Header/footer applied -> %s", output_pdf)
        return True
    except Exception as exc:
        logger.error("Header/footer failed: %s", exc)
        return False


def watermark_pdf(
    input_pdf: str | Path,
    output_pdf: str | Path,
    text: str,
    *,
    fontsize: float = 48,
    rotate: int = 45,
    opacity: float = 0.15,
) -> bool:
    """Apply a text watermark across each page using PyMuPDF.

    Args:
        input_pdf: Input PDF.
        output_pdf: Output PDF.
        text: Watermark text.
        fontsize: Font size.
        rotate: Rotation angle.
        opacity: Opacity (0..1).

    Returns:
        True if successful, otherwise False.
    """
    input_pdf = _as_path(input_pdf)
    output_pdf = _as_path(output_pdf)
    if not input_pdf.exists():
        logger.error("Input PDF not found: %s", input_pdf)
        return False

    try:
        import pymupdf
    except ModuleNotFoundError:
        logger.error("Missing dependency: pymupdf (install with `pip install pymupdf`)")
        return False

    try:
        doc = pymupdf.open(str(input_pdf))
        pages = int(doc.page_count)
        for page_index in range(pages):
            page = doc.load_page(page_index)
            rect = page.rect
            pos = (rect.width / 2, rect.height / 2)
            page.insert_text(
                pos,
                text,
                fontsize=fontsize,
                rotate=int(rotate),
                color=(0.6, 0.6, 0.6),
            )

        _ensure_parent_dir(output_pdf)
        doc.save(str(output_pdf))
        logger.info("Watermark applied -> %s", output_pdf)
        return True
    except Exception as exc:
        logger.error("Watermark failed: %s", exc)
        return False


def extract_images_from_pdf(input_pdf: str | Path, output_dir: str | Path) -> int | None:
    """Extract embedded images from a PDF using PyMuPDF.

    Args:
        input_pdf: Input PDF.
        output_dir: Directory to write extracted images.

    Returns:
        Number of images extracted, or None on failure.
    """
    input_pdf = _as_path(input_pdf)
    output_dir = _as_path(output_dir)
    if not input_pdf.exists():
        logger.error("Input PDF not found: %s", input_pdf)
        return None

    try:
        import pymupdf
    except ModuleNotFoundError:
        logger.error("Missing dependency: pymupdf (install with `pip install pymupdf`)")
        return None

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        doc = pymupdf.open(str(input_pdf))
        count = 0
        pages = int(doc.page_count)
        for page_index in range(1, pages + 1):
            page = doc.load_page(page_index - 1)
            for img in page.get_images(full=True):
                xref = img[0]
                base = doc.extract_image(xref)
                ext = base.get("ext", "bin")
                data = base.get("image")
                if not data:
                    continue
                count += 1
                out = output_dir / f"image_{page_index:04d}_{count:04d}.{ext}"
                with open(out, "wb") as f:
                    f.write(data)
        logger.info("Extracted %d images -> %s", count, output_dir)
        return count
    except Exception as exc:
        logger.error("Image extraction failed: %s", exc)
        return None


def pdf_to_images(
    input_pdf: str | Path,
    output_dir: str | Path,
    *,
    dpi: int = 150,
    fmt: str = "png",
) -> int | None:
    """Render PDF pages to images using PyMuPDF.

    Args:
        input_pdf: Input PDF.
        output_dir: Directory to write page images.
        dpi: Render DPI.
        fmt: Image format ("png" or "jpg").

    Returns:
        Number of pages rendered, or None on failure.
    """
    input_pdf = _as_path(input_pdf)
    output_dir = _as_path(output_dir)
    if not input_pdf.exists():
        logger.error("Input PDF not found: %s", input_pdf)
        return None

    try:
        import pymupdf
    except ModuleNotFoundError:
        logger.error("Missing dependency: pymupdf (install with `pip install pymupdf`)")
        return None

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        doc = pymupdf.open(str(input_pdf))
        zoom = dpi / 72
        mat = pymupdf.Matrix(zoom, zoom)
        fmt = fmt.lower()
        written = 0
        pages = int(doc.page_count)
        for page_index in range(1, pages + 1):
            page = doc.load_page(page_index - 1)
            pix = page.get_pixmap(matrix=mat)
            out = output_dir / f"page_{page_index:04d}.{fmt}"
            pix.save(str(out))
            written += 1
        logger.info("Rendered %d pages -> %s", written, output_dir)
        return written
    except Exception as exc:
        logger.error("PDF->images failed: %s", exc)
        return None


def deocr_selected_pages(
    input_pdf: str | Path,
    output_pdf: str | Path,
    pages: str,
    *,
    dpi: int = 150,
) -> bool:
    """Convert selected PDF pages to image-only pages (remove OCR/text layer).

    The selected pages are rasterized and reinserted as image-only pages,
    while all non-selected pages are preserved as-is.

    Args:
        input_pdf: Input PDF.
        output_pdf: Output PDF.
        pages: 1-based page selection string, e.g. "1,2,9-12,16".
        dpi: Rasterization DPI for converted pages.

    Returns:
        True if successful, otherwise False.

    Notes:
        Requires the third-party package `pymupdf`.
    """
    input_pdf = _as_path(input_pdf)
    output_pdf = _as_path(output_pdf)
    if not input_pdf.exists():
        logger.error("Input PDF not found: %s", input_pdf)
        return False
    if dpi <= 0:
        logger.error("dpi must be > 0")
        return False

    try:
        import pymupdf
    except ModuleNotFoundError:
        logger.error("Missing dependency: pymupdf (install with `pip install pymupdf`)")
        return False

    try:
        src = pymupdf.open(str(input_pdf))
        total_pages = int(src.page_count)
        selected_indices = set(_parse_page_selection(pages, total_pages=total_pages))

        out = pymupdf.open()
        zoom = dpi / 72
        mat = pymupdf.Matrix(zoom, zoom)

        for idx in range(total_pages):
            if idx in selected_indices:
                src_page = src.load_page(idx)
                rect = src_page.rect
                pix = src_page.get_pixmap(matrix=mat, alpha=False)
                new_page = out.new_page(width=rect.width, height=rect.height)
                new_page.insert_image(new_page.rect, pixmap=pix)
            else:
                out.insert_pdf(src, from_page=idx, to_page=idx)

        _ensure_parent_dir(output_pdf)
        out.save(str(output_pdf))
        logger.info(
            "Converted %d selected page(s) to non-OCR -> %s",
            len(selected_indices),
            output_pdf,
        )
        return True
    except ValueError as exc:
        logger.error("Invalid page selection: %s", exc)
        return False
    except Exception as exc:
        logger.error("Selected-page de-OCR failed: %s", exc)
        return False


def show_pdf_metadata(input_pdf: str | Path) -> dict[str, str] | None:
    """Read and log PDF metadata.

    Args:
        input_pdf: Input PDF.

    Returns:
        A dictionary of metadata on success, otherwise None.
    """
    input_pdf = _as_path(input_pdf)
    if not input_pdf.exists():
        logger.error("Input PDF not found: %s", input_pdf)
        return None

    try:
        from pypdf import PdfReader
    except ModuleNotFoundError:
        logger.error("Missing dependency: pypdf (install with `pip install pypdf`)")
        return None

    try:
        reader = PdfReader(str(input_pdf))
        meta = reader.metadata
        result: dict[str, str] = {}
        if meta:
            for k, v in meta.items():
                result[str(k)] = "" if v is None else str(v)
        for k, v in sorted(result.items()):
            logger.info("%s: %s", k, v)
        return result
    except Exception as exc:
        logger.error("Metadata read failed: %s", exc)
        return None


def set_pdf_metadata(input_pdf: str | Path, output_pdf: str | Path, metadata: dict[str, str]) -> bool:
    """Set PDF metadata and write a new PDF.

    Args:
        input_pdf: Input PDF.
        output_pdf: Output PDF.
        metadata: Metadata dictionary. Keys should be like "/Title", "/Author".

    Returns:
        True if successful, otherwise False.
    """
    input_pdf = _as_path(input_pdf)
    output_pdf = _as_path(output_pdf)
    if not input_pdf.exists():
        logger.error("Input PDF not found: %s", input_pdf)
        return False

    try:
        from pypdf import PdfReader, PdfWriter
    except ModuleNotFoundError:
        logger.error("Missing dependency: pypdf (install with `pip install pypdf`)")
        return False

    try:
        reader = PdfReader(str(input_pdf))
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.add_metadata(metadata)

        _ensure_parent_dir(output_pdf)
        with open(output_pdf, "wb") as f:
            writer.write(f)
        logger.info("Metadata updated -> %s", output_pdf)
        return True
    except Exception as exc:
        logger.error("Metadata update failed: %s", exc)
        return False


def batch_process_folder(
    folder: str | Path,
    *,
    glob_pattern: str = "*.pdf",
    operation: str,
    output_dir: str | Path | None = None,
    language: str = "eng",
) -> int:
    """Run an operation on all PDFs in a folder.

    Supported operations:
        - "ocr"
        - "compress"
        - "extract-text"

    Args:
        folder: Folder containing PDFs.
        glob_pattern: Glob pattern to match PDFs.
        operation: Operation name.
        output_dir: Where outputs are written. If None, uses folder.
        language: OCR language (for operation="ocr").

    Returns:
        Number of successfully processed files.
    """
    folder = _as_path(folder)
    if output_dir is None:
        output_dir = folder
    output_dir = _as_path(output_dir)
    if not folder.exists():
        logger.error("Folder not found: %s", folder)
        return 0

    pdfs = sorted(folder.glob(glob_pattern))
    if not pdfs:
        logger.error("No PDFs matched %s in %s", glob_pattern, folder)
        return 0

    ok = 0
    for pdf in pdfs:
        if operation == "ocr":
            out = output_dir / f"{pdf.stem}_ocr.pdf"
            if ocr_pdf(pdf, out, language=language):
                ok += 1
        elif operation == "compress":
            out = output_dir / f"{pdf.stem}_compressed.pdf"
            if compress_pdf(pdf, out):
                ok += 1
        elif operation == "extract-text":
            out = output_dir / f"{pdf.stem}.txt"
            if extract_text_from_pdf(pdf, out) is not None:
                ok += 1
        else:
            logger.error("Unknown batch operation: %s", operation)
            break

    logger.info("Batch complete: %d/%d succeeded", ok, len(pdfs))
    return ok


def _parse_order(value: str) -> list[int]:
    """Parse a comma-separated list of integers."""
    return [int(x.strip()) for x in value.split(",") if x.strip()]


def _parse_page_selection(selection: str, *, total_pages: int) -> list[int]:
    """Parse a page selection string like "1-3,6,10" (1-based, inclusive).

    Returns a list of 0-based page indices in the order specified, with duplicates removed.

    Args:
        selection: Comma-separated pages and ranges (e.g. "9,10,17-115").
        total_pages: Total number of pages in the PDF.

    Raises:
        ValueError: If the selection is invalid or out of range.
    """
    if total_pages <= 0:
        raise ValueError("total_pages must be > 0")

    selection = (selection or "").strip()
    if not selection:
        raise ValueError("empty page selection")

    indices: list[int] = []
    seen: set[int] = set()

    for raw_part in selection.split(","):
        part = raw_part.strip()
        if not part:
            continue

        m_range = re.fullmatch(r"(\d+)\s*-\s*(\d+)", part)
        if m_range:
            start = int(m_range.group(1))
            end = int(m_range.group(2))
            if start <= 0 or end <= 0:
                raise ValueError(f"invalid page number in '{part}'")
            if start > end:
                raise ValueError(f"range start > end in '{part}'")
            if start > total_pages or end > total_pages:
                raise ValueError(f"page range '{part}' out of bounds (1..{total_pages})")
            for page_no in range(start, end + 1):
                idx = page_no - 1
                if idx in seen:
                    continue
                seen.add(idx)
                indices.append(idx)
            continue

        m_single = re.fullmatch(r"\d+", part)
        if m_single:
            page_no = int(part)
            if page_no <= 0 or page_no > total_pages:
                raise ValueError(f"page '{part}' out of bounds (1..{total_pages})")
            idx = page_no - 1
            if idx not in seen:
                seen.add(idx)
                indices.append(idx)
            continue

        raise ValueError(part)

    if not indices:
        raise ValueError("no pages selected")
    return indices


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(prog="pdfsuite", description="Small PDF utility suite")
    parser.add_argument("--log-level", default="INFO", help="DEBUG|INFO|WARNING|ERROR")

    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("menu", help="Interactive menu runner")

    p = sub.add_parser("docx", help="Convert PDF to DOCX")
    p.add_argument("--in", dest="input_pdf", required=True)
    p.add_argument("--out", dest="output_docx", required=True)

    p = sub.add_parser("docx-to-pdf", help="Convert DOCX to PDF")
    p.add_argument("--in", dest="input_docx", required=True)
    p.add_argument("--out", dest="output_pdf", required=True)

    p = sub.add_parser("ocr", help="OCR a scanned PDF")
    p.add_argument("--in", dest="input_pdf", required=True)
    p.add_argument("--out", dest="output_pdf", required=True)
    p.add_argument("--lang", default="eng")
    p.add_argument("--deskew", action="store_true")
    p.add_argument("--rotate-pages", action="store_true")
    p.add_argument("--remove-background", action="store_true")
    p.add_argument("--optimize", type=int, default=1)
    p.add_argument("--force-ocr", action="store_true")
    p.add_argument("--skip-text", action="store_true")

    p = sub.add_parser("merge", help="Merge PDFs")
    p.add_argument("--out", dest="output_pdf", required=True)
    p.add_argument("inputs", nargs="+", help="Input PDFs in order")

    p = sub.add_parser("split", help="Split PDF")
    p.add_argument("--in", dest="input_pdf", required=True)
    p.add_argument("--mode", choices=["single", "range", "chunk"], default="single")
    p.add_argument("--range", dest="page_range", default="1-10")
    p.add_argument("--chunk-size", type=int, default=1)
    p.add_argument("--out-dir", default=".")
    p.add_argument("--prefix", default="")

    p = sub.add_parser("jpg-merge", help="Merge JPG/JPEG to a PDF")
    p.add_argument("--folder", required=True)
    p.add_argument("--out", dest="output_pdf", default="merged_output.pdf")
    p.add_argument("--files", nargs="*", default=None, help="Optional filenames (ordered)")

    p = sub.add_parser("compress", help="Compress PDF")
    p.add_argument("--in", dest="input_pdf", required=True)
    p.add_argument("--out", dest="output_pdf", required=True)

    p = sub.add_parser("extract-text", help="Extract text from PDF to .txt")
    p.add_argument("--in", dest="input_pdf", required=True)
    p.add_argument("--out", dest="output_txt", default=None)

    p = sub.add_parser("encrypt", help="Encrypt PDF")
    p.add_argument("--in", dest="input_pdf", required=True)
    p.add_argument("--out", dest="output_pdf", required=True)
    p.add_argument("--password", required=True)

    p = sub.add_parser("decrypt", help="Decrypt PDF")
    p.add_argument("--in", dest="input_pdf", required=True)
    p.add_argument("--out", dest="output_pdf", required=True)
    p.add_argument("--password", required=True)

    p = sub.add_parser("rotate", help="Rotate PDF pages")
    p.add_argument("--in", dest="input_pdf", required=True)
    p.add_argument("--out", dest="output_pdf", required=True)
    p.add_argument("--angle", type=int, required=True)
    p.add_argument("--pages", default=None)

    p = sub.add_parser("delete-pages", help="Delete pages from PDF")
    p.add_argument("--in", dest="input_pdf", required=True)
    p.add_argument("--out", dest="output_pdf", required=True)
    p.add_argument("--pages", required=True)

    p = sub.add_parser("reorder", help="Reorder PDF pages")
    p.add_argument("--in", dest="input_pdf", required=True)
    p.add_argument("--out", dest="output_pdf", required=True)
    p.add_argument("--order", required=True, help="Comma-separated order, e.g. 2,1,3")

    p = sub.add_parser("header-footer", help="Add header/footer text")
    p.add_argument("--in", dest="input_pdf", required=True)
    p.add_argument("--out", dest="output_pdf", required=True)
    p.add_argument("--header", default=None)
    p.add_argument("--footer", default=None)
    p.add_argument("--margin", type=float, default=36)
    p.add_argument("--fontsize", type=float, default=10)

    p = sub.add_parser("watermark", help="Add a text watermark")
    p.add_argument("--in", dest="input_pdf", required=True)
    p.add_argument("--out", dest="output_pdf", required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--fontsize", type=float, default=48)
    p.add_argument("--rotate", type=float, default=45)
    p.add_argument("--opacity", type=float, default=0.15)

    p = sub.add_parser("extract-images", help="Extract embedded images")
    p.add_argument("--in", dest="input_pdf", required=True)
    p.add_argument("--out-dir", required=True)

    p = sub.add_parser("to-images", help="Render PDF pages to images")
    p.add_argument("--in", dest="input_pdf", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--dpi", type=int, default=150)
    p.add_argument("--fmt", default="png")

    p = sub.add_parser("deocr-pages", help="Convert selected pages to non-OCR (image-only)")
    p.add_argument("--in", dest="input_pdf", required=True)
    p.add_argument("--out", dest="output_pdf", required=True)
    p.add_argument("--pages", required=True, help='Page selection, e.g. "1,2,9-12,16"')
    p.add_argument("--dpi", type=int, default=150)

    p = sub.add_parser("meta-show", help="Show PDF metadata")
    p.add_argument("--in", dest="input_pdf", required=True)

    p = sub.add_parser("meta-set", help="Set PDF metadata")
    p.add_argument("--in", dest="input_pdf", required=True)
    p.add_argument("--out", dest="output_pdf", required=True)
    p.add_argument("--json", dest="json_metadata", required=True, help='JSON dict like {"/Title":"X"}')

    p = sub.add_parser("info", help="Show quick PDF info")
    p.add_argument("--in", dest="input_pdf", required=True)

    p = sub.add_parser("batch", help="Batch process a folder")
    p.add_argument("--folder", required=True)
    p.add_argument("--op", required=True, choices=["ocr", "compress", "extract-text"])
    p.add_argument("--glob", dest="glob_pattern", default="*.pdf")
    p.add_argument("--out-dir", dest="output_dir", default=None)
    p.add_argument("--lang", default="eng")

    return parser


def _prompt(value_name: str, *, default: str | None = None) -> str:
    """Prompt the user for a string value.

    Args:
        value_name: Label shown to the user.
        default: Optional default returned when user enters blank input.

    Returns:
        The user input (or default).
    """
    suffix = f" [default: {default}]" if default is not None else ""
    raw = input(f"{value_name}{suffix}: ").strip()
    if not raw and default is not None:
        return default
    return raw


def _prompt_int(value_name: str, *, default: int | None = None) -> int:
    """Prompt the user for an integer value."""
    while True:
        raw = _prompt(value_name, default=str(default) if default is not None else None)
        try:
            return int(raw)
        except ValueError:
            logger.error("Invalid number: %s", raw)


def _prompt_float(value_name: str, *, default: float | None = None) -> float:
    """Prompt the user for a float value."""
    while True:
        raw = _prompt(value_name, default=str(default) if default is not None else None)
        try:
            return float(raw)
        except ValueError:
            logger.error("Invalid number: %s", raw)


def interactive_menu() -> int:
    """Run an interactive menu runner.

    Returns:
        Process exit code (0 for success, 1 for failure).
    """
    while True:
        logger.info("\nPDFSuite Menu")
        logger.info("1) PDF -> DOCX")
        logger.info("2) OCR PDF")
        logger.info("3) Merge PDFs")
        logger.info("4) Split PDF")
        logger.info("5) Merge JPG/JPEG -> PDF")
        logger.info("6) Compress PDF")
        logger.info("7) Extract text")
        logger.info("8) Encrypt PDF")
        logger.info("9) Decrypt PDF")
        logger.info("10) Rotate pages")
        logger.info("11) Delete pages")
        logger.info("12) Reorder pages")
        logger.info("13) Add header/footer")
        logger.info("14) Watermark")
        logger.info("15) Extract images")
        logger.info("16) PDF -> images")
        logger.info("17) Show metadata")
        logger.info("18) Set metadata")
        logger.info("19) PDF info (pages/encrypted)")
        logger.info("20) Batch folder")
        logger.info("21) Convert selected pages to non-OCR")
        logger.info("22) DOCX -> PDF")
        logger.info("0) Exit")

        choice = _prompt("Choose", default="0")
        if choice in {"0", "q", "quit", "exit"}:
            return 0

        try:
            if choice == "1":
                inp = _prompt("Input PDF")
                out = _prompt("Output DOCX")
                return 0 if pdf_to_docx(inp, out) else 1

            if choice == "22":
                inp = _prompt("Input DOCX")
                out = _prompt("Output PDF")
                return 0 if docx_to_pdf(inp, out) else 1

            if choice == "2":
                inp = _prompt("Input PDF")
                out = _prompt("Output PDF")
                lang = _prompt("Language", default="eng")
                deskew = _prompt("Deskew? (y/n)", default="n").lower().startswith("y")
                rotate_pages = _prompt("Rotate pages? (y/n)", default="n").lower().startswith("y")
                remove_bg = _prompt("Remove background? (y/n)", default="n").lower().startswith("y")
                optimize = _prompt_int("Optimize (0-3)", default=1)
                force_ocr = _prompt("Force OCR? (y/n)", default="n").lower().startswith("y")
                skip_text = _prompt("Skip existing text? (y/n)", default="n").lower().startswith("y")
                ok = ocr_pdf(
                    inp,
                    out,
                    language=lang,
                    deskew=deskew,
                    rotate_pages=rotate_pages,
                    remove_background=remove_bg,
                    optimize=optimize,
                    force_ocr=force_ocr,
                    skip_text=skip_text,
                )
                return 0 if ok else 1

            if choice == "3":
                out = _prompt("Output merged PDF")
                raw = _prompt("Input PDFs (comma-separated)")
                inputs = [p.strip() for p in raw.split(",") if p.strip()]
                return 0 if merge_pdfs(inputs, out) else 1

            if choice == "4":
                inp = _prompt("Input PDF")
                mode = _prompt("Mode (single/range/chunk)", default="single").strip().lower()
                out_dir = _prompt("Output directory", default=".")
                prefix = _prompt("Filename prefix (optional)", default="")
                pr = _prompt("Page range (for mode=range)", default="1-10")
                chunk = _prompt_int("Chunk size (for mode=chunk)", default=10)
                ok = split_pdf(inp, mode=mode, page_range=pr, chunk_size=chunk, output_dir=out_dir, prefix=prefix)
                return 0 if ok else 1

            if choice == "5":
                folder = _prompt("Image folder")
                out = _prompt("Output PDF", default="merged_output.pdf")
                raw = _prompt("Filenames (comma-separated, optional)", default="")
                files = [x.strip() for x in raw.split(",") if x.strip()] if raw else None
                return 0 if jpeg_to_pdf_merge(folder, files, out) else 1

            if choice == "6":
                inp = _prompt("Input PDF")
                out = _prompt("Output PDF")
                return 0 if compress_pdf(inp, out) else 1

            if choice == "7":
                inp = _prompt("Input PDF")
                out = _prompt("Output TXT (optional)", default="")
                out_path = out if out else None
                return 0 if extract_text_from_pdf(inp, out_path) is not None else 1

            if choice == "8":
                inp = _prompt("Input PDF")
                out = _prompt("Output encrypted PDF")
                pw = _prompt("Password")
                return 0 if encrypt_pdf(inp, out, pw) is not None else 1

            if choice == "9":
                inp = _prompt("Input PDF")
                out = _prompt("Output decrypted PDF")
                pw = _prompt("Password")
                return 0 if decrypt_pdf(inp, out, pw) is not None else 1

            if choice == "10":
                inp = _prompt("Input PDF")
                out = _prompt("Output PDF")
                angle = _prompt_int("Angle (90/180/270)", default=90)
                pages = _prompt("Pages (optional, e.g. 1-3,6)", default="")
                pages_val = pages if pages else None
                return 0 if rotate_pdf(inp, out, angle, pages=pages_val) else 1

            if choice == "11":
                inp = _prompt("Input PDF")
                out = _prompt("Output PDF")
                pages = _prompt("Pages to delete (e.g. 1-3,6)")
                return 0 if delete_pages_pdf(inp, out, pages) else 1

            if choice == "12":
                inp = _prompt("Input PDF")
                out = _prompt("Output PDF")
                order_raw = _prompt("New order (comma-separated, e.g. 2,1,3)")
                return 0 if reorder_pages_pdf(inp, out, _parse_order(order_raw)) else 1

            if choice == "13":
                inp = _prompt("Input PDF")
                out = _prompt("Output PDF")
                header = _prompt('Header (optional, supports {page}/{pages})', default="")
                footer = _prompt('Footer (optional, supports {page}/{pages})', default="")
                margin = _prompt_float("Margin (points)", default=36)
                fontsize = _prompt_float("Font size", default=10)
                return 0 if add_header_footer_pdf(
                    inp,
                    out,
                    header=header or None,
                    footer=footer or None,
                    margin=margin,
                    fontsize=fontsize,
                ) else 1

            if choice == "14":
                inp = _prompt("Input PDF")
                out = _prompt("Output PDF")
                text = _prompt("Watermark text")
                fontsize = _prompt_float("Font size", default=48)
                rotate = _prompt_int("Rotate", default=45)
                opacity = _prompt_float("Opacity (0..1)", default=0.15)
                return 0 if watermark_pdf(inp, out, text, fontsize=fontsize, rotate=rotate, opacity=opacity) else 1

            if choice == "15":
                inp = _prompt("Input PDF")
                out_dir = _prompt("Output directory")
                return 0 if extract_images_from_pdf(inp, out_dir) is not None else 1

            if choice == "16":
                inp = _prompt("Input PDF")
                out_dir = _prompt("Output directory")
                dpi = _prompt_int("DPI", default=150)
                fmt = _prompt("Format (png/jpg)", default="png")
                return 0 if pdf_to_images(inp, out_dir, dpi=dpi, fmt=fmt) is not None else 1

            if choice == "17":
                inp = _prompt("Input PDF")
                return 0 if show_pdf_metadata(inp) is not None else 1

            if choice == "18":
                inp = _prompt("Input PDF")
                out = _prompt("Output PDF")
                raw = _prompt('Metadata JSON (e.g. {"/Title":"X"})')
                try:
                    md = json.loads(raw)
                    if not isinstance(md, dict):
                        raise ValueError("metadata must be a JSON object")
                    md = {str(k): str(v) for k, v in md.items()}
                except Exception as exc:
                    logger.error("Invalid JSON: %s", exc)
                    return 1
                return 0 if set_pdf_metadata(inp, out, md) else 1

            if choice == "19":
                inp = _prompt("Input PDF")
                pages = pdf_page_count(inp)
                enc = pdf_is_encrypted(inp)
                if pages is None or enc is None:
                    return 1
                logger.info("Pages: %s", pages)
                logger.info("Encrypted: %s", enc)
                return 0

            if choice == "20":
                folder = _prompt("Folder")
                op = _prompt("Operation (ocr/compress/extract-text)")
                glob_pattern = _prompt("Glob", default="*.pdf")
                out_dir = _prompt("Output directory (optional)", default="")
                out_dir_val = out_dir if out_dir else None
                lang = _prompt("Language (ocr)", default="eng")
                ok = batch_process_folder(
                    folder,
                    glob_pattern=glob_pattern,
                    operation=op,
                    output_dir=out_dir_val,
                    language=lang,
                )
                return 0 if ok > 0 else 1

            if choice == "21":
                inp = _prompt("Input PDF")
                out = _prompt("Output PDF")
                pages = _prompt('Pages to convert (e.g. 1,2,9-12,16)')
                dpi = _prompt_int("DPI", default=150)
                return 0 if deocr_selected_pages(inp, out, pages, dpi=dpi) else 1

            logger.error("Unknown choice: %s", choice)
        except KeyboardInterrupt:
            logger.info("\nCancelled.")
            return 1




def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    if argv is None and len(sys.argv) == 1:
        configure_logging("INFO")
        return interactive_menu()

    parser = build_arg_parser()
    args = parser.parse_args(argv)
    configure_logging(args.log_level)

    cmd = args.cmd
    if cmd == "menu":
        return interactive_menu()
    if cmd == "docx":
        return 0 if pdf_to_docx(args.input_pdf, args.output_docx) else 1

    if cmd == "docx-to-pdf":
        return 0 if docx_to_pdf(args.input_docx, args.output_pdf) else 1

    if cmd == "ocr":
        ok = ocr_pdf(
            args.input_pdf,
            args.output_pdf,
            language=args.lang,
            deskew=args.deskew,
            rotate_pages=args.rotate_pages,
            remove_background=args.remove_background,
            optimize=args.optimize,
            force_ocr=args.force_ocr,
            skip_text=args.skip_text,
        )
        return 0 if ok else 1

    if cmd == "merge":
        return 0 if merge_pdfs(args.inputs, args.output_pdf) else 1

    if cmd == "split":
        return 0 if split_pdf(
            args.input_pdf,
            mode=args.mode,
            page_range=args.page_range,
            chunk_size=args.chunk_size,
            output_dir=args.out_dir,
            prefix=args.prefix,
        ) else 1

    if cmd == "jpg-merge":
        return 0 if jpeg_to_pdf_merge(args.folder, args.files, args.output_pdf) else 1

    if cmd == "compress":
        return 0 if compress_pdf(args.input_pdf, args.output_pdf) else 1

    if cmd == "extract-text":
        out = extract_text_from_pdf(args.input_pdf, args.output_txt)
        return 0 if out is not None else 1

    if cmd == "encrypt":
        out = encrypt_pdf(args.input_pdf, args.output_pdf, args.password)
        return 0 if out is not None else 1

    if cmd == "decrypt":
        out = decrypt_pdf(args.input_pdf, args.output_pdf, args.password)
        return 0 if out is not None else 1

    if cmd == "rotate":
        return 0 if rotate_pdf(args.input_pdf, args.output_pdf, args.angle, pages=args.pages) else 1

    if cmd == "delete-pages":
        return 0 if delete_pages_pdf(args.input_pdf, args.output_pdf, args.pages) else 1

    if cmd == "reorder":
        order = _parse_order(args.order)
        return 0 if reorder_pages_pdf(args.input_pdf, args.output_pdf, order) else 1

    if cmd == "header-footer":
        return 0 if add_header_footer_pdf(
            args.input_pdf,
            args.output_pdf,
            header=args.header,
            footer=args.footer,
            margin=args.margin,
            fontsize=args.fontsize,
        ) else 1

    if cmd == "watermark":
        return 0 if watermark_pdf(
            args.input_pdf,
            args.output_pdf,
            args.text,
            fontsize=args.fontsize,
            rotate=args.rotate,
            opacity=args.opacity,
        ) else 1

    if cmd == "extract-images":
        count = extract_images_from_pdf(args.input_pdf, args.out_dir)
        return 0 if count is not None else 1

    if cmd == "to-images":
        count = pdf_to_images(args.input_pdf, args.out_dir, dpi=args.dpi, fmt=args.fmt)
        return 0 if count is not None else 1

    if cmd == "deocr-pages":
        return 0 if deocr_selected_pages(args.input_pdf, args.output_pdf, args.pages, dpi=args.dpi) else 1

    if cmd == "meta-show":
        meta = show_pdf_metadata(args.input_pdf)
        return 0 if meta is not None else 1

    if cmd == "meta-set":
        try:
            md = json.loads(args.json_metadata)
            if not isinstance(md, dict):
                raise ValueError("metadata must be a JSON object")
            md = {str(k): str(v) for k, v in md.items()}
        except Exception as exc:
            logger.error("Invalid --json value: %s", exc)
            return 1
        return 0 if set_pdf_metadata(args.input_pdf, args.output_pdf, md) else 1

    if cmd == "info":
        pages = pdf_page_count(args.input_pdf)
        enc = pdf_is_encrypted(args.input_pdf)
        if pages is None or enc is None:
            return 1
        logger.info("Pages: %s", pages)
        logger.info("Encrypted: %s", enc)
        return 0

    if cmd == "batch":
        ok = batch_process_folder(
            args.folder,
            glob_pattern=args.glob_pattern,
            operation=args.op,
            output_dir=args.output_dir,
            language=args.lang,
        )
        return 0 if ok > 0 else 1

    logger.error("Unknown command")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
