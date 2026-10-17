import argparse
import csv
import getpass
import io
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Iterable, NamedTuple, Sequence

try:
    # Used by almost every feature, so loaded once here. The other libraries
    # are loaded only by the features that need them, to keep start-up fast.
    import pymupdf
    from pypdf import PdfReader, PdfWriter
    from pypdf.errors import FileNotDecryptedError
except ModuleNotFoundError as exc:  # setup did not finish
    sys.exit(f"Missing Python package: {exc.name}. Run setupEnv.bat again.")


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


def _open_pdf_for_edit(path: Path) -> "pymupdf.Document":
    """Open a PDF with PyMuPDF from a copy in memory.

    The file on disk is not kept open, so the result can be saved over the
    original (output = input), which PyMuPDF refuses for a file it has open.
    """
    return pymupdf.open(stream=path.read_bytes(), filetype="pdf")


def _natural_sort_key(name: str) -> list[int | str]:
    """Sort key that orders embedded numbers numerically ("img2" before "img10")."""
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", name)]


_IS_WINDOWS = os.name == "nt"


def _windows_program_dirs() -> list[Path]:
    """Folders Windows installers usually put programs in (all-users and per-user)."""
    dirs: list[Path] = []
    for var in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
        value = os.environ.get(var)
        if value:
            dirs.append(Path(value))
    local = os.environ.get("LOCALAPPDATA")
    if local:
        dirs.append(Path(local) / "Programs")
    unique: list[Path] = []
    for d in dirs:
        if d not in unique:
            unique.append(d)
    return unique


def _find_program(names: Sequence[str], windows_patterns: Sequence[str] = ()) -> str | None:
    """Find a program on PATH, or on Windows in the usual install folders.

    Many Windows installers (Ghostscript, LibreOffice) do not add themselves
    to PATH, so PATH alone misses them.

    Args:
        names: Executable names to look up on PATH, in order of preference.
        windows_patterns: Glob patterns relative to each Program Files folder,
            e.g. "gs/*/bin/gswin64c.exe". When several match, the one with the
            highest version-like name wins.

    Returns:
        Full path to the program, or None if not found.
    """
    for name in names:
        resolved = shutil.which(name)
        if resolved:
            return resolved
    if not _IS_WINDOWS:
        return None
    for base in _windows_program_dirs():
        for pattern in windows_patterns:
            matches = sorted(base.glob(pattern), key=lambda p: _natural_sort_key(str(p)))
            if matches:
                return str(matches[-1])
    return None


def _registry_values(key_path: str, value_name: str) -> list[str]:
    """Read a string value from HKEY_LOCAL_MACHINE and HKEY_CURRENT_USER (Windows only)."""
    if not _IS_WINDOWS:
        return []
    import winreg

    found: list[str] = []
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(hive, key_path) as key:
                value, _ = winreg.QueryValueEx(key, value_name)
                if value:
                    found.append(str(value))
        except OSError:
            continue
    return found


def _registry_subkeys(key_path: str) -> list[str]:
    """Names of a registry key's subkeys in both hives (Windows only)."""
    if not _IS_WINDOWS:
        return []
    import winreg

    names: list[str] = []
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(hive, key_path) as key:
                i = 0
                while True:
                    try:
                        names.append(winreg.EnumKey(key, i))
                    except OSError:
                        break
                    i += 1
        except OSError:
            continue
    return names


def _first_file(dirs: Iterable[Path], names: Sequence[str]) -> str | None:
    """Return the first dirs/name that exists, trying every name in each folder."""
    for d in dirs:
        for name in names:
            candidate = d / name
            if candidate.is_file():
                return str(candidate)
    return None


# Installers record where they put these programs in the registry. ocrmypdf
# looks there too, so checking it finds installs in custom folders that it
# can use but PATH and Program Files don't show.
_GS_REGISTRY_KEY = r"SOFTWARE\Artifex\GPL Ghostscript"
_TESSERACT_REGISTRY_KEY = r"SOFTWARE\Tesseract-OCR"


def _find_ghostscript() -> str | None:
    """Find the Ghostscript console program (gswin64c/gswin32c on Windows)."""
    exes = ("gswin64c.exe", "gswin32c.exe")
    found = _find_program(
        ("gswin64c", "gswin32c", "gs"),
        tuple(f"gs/*/bin/{exe}" for exe in exes),
    )
    if found or not _IS_WINDOWS:
        return found
    # Newest version first; GS_DLL is the DLL inside Ghostscript's bin folder.
    versions = sorted(set(_registry_subkeys(_GS_REGISTRY_KEY)), key=_natural_sort_key, reverse=True)
    dll_paths = [
        dll for ver in versions for dll in _registry_values(f"{_GS_REGISTRY_KEY}\\{ver}", "GS_DLL")
    ]
    return _first_file((Path(dll).parent for dll in dll_paths), exes)


def _find_tesseract() -> str | None:
    """Find Tesseract OCR."""
    found = _find_program(("tesseract",), ("Tesseract-OCR/tesseract.exe",))
    if found or not _IS_WINDOWS:
        return found
    install_dirs = _registry_values(_TESSERACT_REGISTRY_KEY, "InstallDir")
    return _first_file((Path(d) for d in install_dirs), ("tesseract.exe",))


def _find_soffice() -> str | None:
    """Find LibreOffice's command-line program."""
    return _find_program(("soffice", "libreoffice"), ("LibreOffice/program/soffice.exe",))


def _word_installed() -> bool | None:
    """Whether Microsoft Word is registered for automation (None when not on Windows)."""
    if not _IS_WINDOWS:
        return None
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "Word.Application"):
            return True
    except OSError:
        return False


def _parse_metadata_json(raw: str) -> dict[str, str]:
    """Parse a JSON object of PDF metadata into a str->str dict.

    Raises:
        ValueError: If the JSON is invalid or not an object.
    """
    md = json.loads(raw)
    if not isinstance(md, dict):
        raise ValueError("metadata must be a JSON object")
    return {str(k): str(v) for k, v in md.items()}


def _fill_page_placeholders(template: str, *, page: int, pages: int) -> str:
    """Replace {page}/{pages} without str.format, so other braces are kept literally."""
    return template.replace("{pages}", str(pages)).replace("{page}", str(page))


# Fonts with wide Unicode coverage, tried in order for text the built-in
# Helvetica cannot encode. PyMuPDF's bundled CJK font is the last resort.
_UNICODE_FONT_CANDIDATES = (
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\Nirmala.ttc",
    r"C:\Windows\Fonts\YuGothM.ttc",
    r"C:\Windows\Fonts\msgothic.ttc",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\malgun.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
)


def _pick_font(pymupdf: object, text: str) -> tuple[dict, object]:
    """Choose a font able to render `text`.

    Returns:
        (insert_text font kwargs, pymupdf.Font for measuring the text).
    """
    try:
        text.encode("latin-1")
        return {"fontname": "helv"}, pymupdf.Font("helv")
    except UnicodeEncodeError:
        pass

    needed = {ord(ch) for ch in text if not ch.isspace()}
    for candidate in _UNICODE_FONT_CANDIDATES:
        if not os.path.isfile(candidate):
            continue
        try:
            font = pymupdf.Font(fontfile=candidate)
        except Exception:
            continue
        if all(font.has_glyph(cp) for cp in needed):
            logger.debug("Using font %s for non-Latin text", candidate)
            return {"fontname": "unifont", "fontfile": candidate}, font

    logger.debug("No system font covers the text; using PyMuPDF's CJK font")
    return {"fontname": "japan"}, pymupdf.Font("japan")


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

    cv = None
    try:
        _ensure_parent_dir(output_docx)
        cv = Converter(str(input_pdf))
        cv.convert(str(output_docx))
        logger.info("Converted PDF -> DOCX: %s", output_docx)
        return True
    except Exception as exc:
        logger.error("PDF->DOCX failed: %s", exc)
        return False
    finally:
        if cv is not None:
            cv.close()


# LibreOffice is given this long to convert one document before it is stopped
# (a hidden dialog, such as document recovery, would otherwise wait forever).
_LIBREOFFICE_TIMEOUT_SECONDS = 300


def docx_to_pdf(input_docx: str | Path, output_pdf: str | Path) -> bool:
    """Convert a DOCX file to PDF.

    Uses Microsoft Word (through the `docx2pdf` package) when it is installed,
    and falls back to a headless LibreOffice (`soffice`) conversion.
    """
    input_docx = _as_path(input_docx)
    output_pdf = _as_path(output_pdf)
    if not input_docx.exists():
        logger.error("Input DOCX not found: %s", input_docx)
        return False

    try:
        # Both converters write into a fresh temporary folder, and the result is
        # moved to output_pdf only once it exists. Checking output_pdf itself
        # would mistake an older file at that path for a successful conversion.
        # ignore_cleanup_errors: a LibreOffice helper process can still hold a
        # file here for a moment, which must not turn success into failure.
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_name:
            tmp = Path(tmp_name)
            produced = tmp / (input_docx.stem + ".pdf")
            backend = None

            # docx2pdf drives Microsoft Word, so only try it where Word can exist.
            if sys.platform == "darwin" or _word_installed():
                try:
                    from docx2pdf import convert

                    convert(str(input_docx), str(produced))
                    # docx2pdf can return without raising when Word fails to export.
                    if produced.is_file():
                        backend = "Microsoft Word"
                    else:
                        logger.warning("Microsoft Word did not produce a PDF; trying LibreOffice")
                except ModuleNotFoundError:
                    logger.debug("docx2pdf not available, will try LibreOffice")
                except Exception as exc:
                    logger.warning("Microsoft Word conversion failed: %s", exc)
            else:
                logger.debug("Microsoft Word not found, will try LibreOffice")

            if backend is None:
                produced.unlink(missing_ok=True)
                if not _convert_with_libreoffice(input_docx, tmp):
                    return False
                backend = "LibreOffice"

            _ensure_parent_dir(output_pdf)
            shutil.move(str(produced), str(output_pdf))
        logger.info("Converted DOCX -> PDF via %s: %s", backend, output_pdf)
        return True
    except Exception as exc:
        logger.error("DOCX->PDF conversion failed: %s", exc)
        return False


def _libreoffice_profile_dir() -> Path:
    """JAP-T's own LibreOffice profile folder, kept between runs."""
    base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
    return Path(base) / "JAP-T" / "libreoffice-profile"


def _convert_with_libreoffice(input_docx: Path, out_dir: Path) -> bool:
    """Convert input_docx to out_dir/<name>.pdf with headless LibreOffice.

    Returns:
        True only if the PDF was written.
    """
    soffice = _find_soffice()
    if not soffice:
        logger.error("No conversion backend available. Install Microsoft Word or LibreOffice.")
        return False

    # JAP-T's own profile: with the normal one, an already-open LibreOffice
    # window takes over the job and nothing is written. It is kept between
    # runs because setting up a new profile is slow.
    profile = _libreoffice_profile_dir()
    cmd = [
        soffice,
        f"-env:UserInstallation={profile.as_uri()}",
        "--headless",
        "--norestore",
        "--convert-to",
        "pdf",
        "--outdir",
        str(out_dir),
        str(input_docx),
    ]
    expected = out_dir / (input_docx.stem + ".pdf")
    output = ""
    # The first run with a new profile only sets the profile up and may exit
    # without converting, so a run that writes nothing is tried once more.
    for _attempt in range(2):
        try:
            # LibreOffice prints UTF-8 (e.g. non-English file names), not the
            # Windows code page, so decode it explicitly and never fail on it.
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=_LIBREOFFICE_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            logger.error(
                "LibreOffice did not finish within %d seconds and was stopped.",
                _LIBREOFFICE_TIMEOUT_SECONDS,
            )
            return False
        output = (completed.stderr or completed.stdout or "").strip()
        if completed.returncode != 0:
            logger.error("LibreOffice conversion failed: %s", output)
            return False
        if expected.is_file():
            return True
        logger.debug("LibreOffice finished without writing %s; trying again", expected.name)

    logger.error("LibreOffice did not produce a PDF for %s. %s", input_docx.name, output)
    return False


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
        result = ocrmypdf.ocr(
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
        # Some failures (e.g. an invalid output PDF) are reported via the
        # return code rather than an exception.
        if result != ocrmypdf.ExitCode.ok:
            logger.error("OCR failed with exit code %s", getattr(result, "name", result))
            return False
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
        writer = PdfWriter()
        for path in resolved:
            # append() keeps each input's bookmarks and form fields.
            writer.append(PdfReader(str(path)))

        _ensure_parent_dir(output_pdf)
        with open(output_pdf, "wb") as f:
            writer.write(f)
        logger.info("Merged %d PDFs -> %s", len(resolved), output_pdf)
        return True
    except Exception as exc:
        logger.error("Merge failed: %s", exc)
        return False


# Image types images_to_pdf picks up from a folder.
_IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif", ".webp")


def _image_for_img2pdf(path: Path) -> str | bytes:
    """Return what img2pdf should embed for one image file.

    img2pdf embeds JPEG, and PNG/TIFF without transparency, as-is (no quality
    loss). Anything else (BMP, GIF, WebP, or images with transparency)
    is converted to PNG with Pillow first; transparent areas become white.
    """
    if path.suffix.lower() in {".jpg", ".jpeg"}:
        return str(path)

    from PIL import Image, ImageOps

    with Image.open(path) as img:
        has_alpha = "A" in img.getbands() or "transparency" in img.info
        if img.format in {"PNG", "TIFF"} and not has_alpha:
            return str(path)

        dpi = img.info.get("dpi")
        converted = ImageOps.exif_transpose(img)
        if has_alpha:
            rgba = converted.convert("RGBA")
            converted = Image.new("RGB", rgba.size, "white")
            converted.paste(rgba, mask=rgba.getchannel("A"))
        elif converted.mode not in {"RGB", "L"}:
            converted = converted.convert("RGB")

        buf = io.BytesIO()
        converted.save(buf, format="PNG", **({"dpi": dpi} if dpi else {}))
        return buf.getvalue()


def images_to_pdf(
    image_folder: str | Path,
    image_files: Sequence[str] | None = None,
    output_pdf: str | Path = "merged_output.pdf",
) -> bool:
    """Combine images into a single PDF, one image per page.

    Supports JPG, PNG, TIFF, BMP, GIF and WebP.

    Args:
        image_folder: Folder containing images.
        image_files: Optional list of filenames (order is preserved). If None,
            uses every supported image in the folder, in natural name order.
        output_pdf: Output PDF path. If relative, it is created inside image_folder.

    Returns:
        True if successful, otherwise False.

    Notes:
        Requires the third-party packages `img2pdf` and `pillow`. JPEG data
        is embedded as-is (no lossy re-encode) and EXIF orientation is applied.
    """
    image_folder = _as_path(image_folder)
    output_pdf = _as_path(output_pdf)
    if not output_pdf.is_absolute():
        output_pdf = image_folder / output_pdf

    if not image_folder.exists():
        logger.error("Image folder not found: %s", image_folder)
        return False

    try:
        import img2pdf
    except ModuleNotFoundError:
        logger.error("Missing dependency: img2pdf (install with `pip install img2pdf`)")
        return False

    try:
        if image_files is None:
            image_files = sorted(
                (
                    p.name
                    for p in image_folder.iterdir()
                    if p.is_file() and p.suffix.lower() in _IMAGE_SUFFIXES
                ),
                key=_natural_sort_key,
            )

        if not image_files:
            logger.error("No images found in: %s", image_folder)
            return False

        # Explicitly listed files must all exist; silently skipping one would
        # produce a PDF with pages missing.
        missing = [name for name in image_files if not (image_folder / name).is_file()]
        if missing:
            logger.error("Images not found in %s: %s", image_folder, ", ".join(missing))
            return False

        images: list[str | bytes] = []
        for filename in image_files:
            img_path = image_folder / filename
            try:
                images.append(_image_for_img2pdf(img_path))
            except Exception as exc:
                logger.error("Cannot read image %s: %s", img_path.name, exc)
                return False
            logger.info("Added image: %s", img_path.name)

        # img2pdf embeds the compressed image bytes directly instead of holding
        # decoded bitmaps in memory and re-encoding them.
        pdf_bytes = img2pdf.convert(images, rotation=img2pdf.Rotation.ifvalid)
        _ensure_parent_dir(output_pdf)
        with open(output_pdf, "wb") as f:
            f.write(pdf_bytes)
        logger.info("Created PDF: %s (%d images)", output_pdf, len(images))
        return True
    except Exception as exc:
        logger.error("Images->PDF failed: %s", exc)
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
            # Clamp so the default "1-10" also works on shorter PDFs.
            indices = _parse_page_selection(page_range, total_pages=total, clamp_end=True)

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
    2) PyMuPDF: lossless cleanup/deflate/garbage collection.
    3) pikepdf: qpdf-style stream/object compression.

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

    before = _size(input_pdf)

    def _log_sizes(method: str) -> None:
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
            completed = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
            if completed.returncode != 0:
                stderr = (completed.stderr or "").strip()
                logger.warning("Ghostscript failed (%s, rc=%s): %s", profile, completed.returncode, stderr)
                return False
            return True
        except Exception as exc:
            logger.warning("Ghostscript failed (%s): %s", profile, exc)
            return False

    def _mktemp_pdf() -> Path:
        fd, name = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        return Path(name)

    def _compress_with_ghostscript_auto(out_path: Path) -> str | None:
        """Write the better of /ebook and /screen to out_path; return the method label."""
        if not _find_ghostscript():
            return None
        if not _run_ghostscript("ebook", out_path):
            return None

        ebook_size = _size(out_path)
        # If /ebook barely helps, try /screen and keep the smaller of the two.
        if before > 0 and ebook_size > 0 and ((before - ebook_size) / before) * 100 < 2.0:
            tmp_screen = _mktemp_pdf()
            try:
                if _run_ghostscript("screen", tmp_screen) and 0 < _size(tmp_screen) < ebook_size:
                    os.replace(tmp_screen, out_path)
                    return "ghostscript/screen"
            finally:
                tmp_screen.unlink(missing_ok=True)
        return "ghostscript/ebook"

    def _compress_with_pymupdf_lossless(out_path: Path) -> str | None:
        try:
            with pymupdf.open(str(input_pdf)) as doc:
                # garbage/clean/deflate are safe and remove unused objects.
                doc.save(
                    str(out_path),
                    garbage=4,
                    clean=True,
                    deflate=True,
                    deflate_images=True,
                    deflate_fonts=True,
                )
            return "pymupdf(lossless)"
        except Exception as exc:
            logger.warning("PyMuPDF compression failed: %s", exc)
            return None

    def _compress_with_pikepdf_lossless(out_path: Path) -> str | None:
        import pikepdf

        try:
            with pikepdf.open(str(input_pdf)) as pdf:
                pdf.save(
                    str(out_path),
                    compress_streams=True,
                    object_stream_mode=pikepdf.ObjectStreamMode.generate,
                    linearize=True,
                )
            return "pikepdf(lossless)"
        except Exception as exc:
            logger.warning("pikepdf compression failed: %s", exc)
            return None

    # 1) Prefer Ghostscript for substantial reductions (especially scanned/image PDFs).
    #    'ebook' is a reasonable default tradeoff (smaller than 'printer', better than 'screen').
    # 2) Lossless fallbacks.
    # Each method writes to a temp file; a result is only kept if it is smaller
    # than the input, so "compression" never produces a bigger file.
    tmp = None
    try:
        tmp = _mktemp_pdf()
        for strategy in (
            _compress_with_ghostscript_auto,
            _compress_with_pymupdf_lossless,
            _compress_with_pikepdf_lossless,
        ):
            method = strategy(tmp)
            if method is None:
                continue
            after = _size(tmp)
            if after > 0 and (before <= 0 or after < before):
                _ensure_parent_dir(output_pdf)
                shutil.copyfile(tmp, output_pdf)
                _log_sizes(method)
                return True
            logger.info("%s did not reduce size (%d -> %d bytes)", method, before, after)

        logger.info("PDF is already optimized; writing an unchanged copy -> %s", output_pdf)
        if not (output_pdf.exists() and os.path.samefile(input_pdf, output_pdf)):
            _ensure_parent_dir(output_pdf)
            shutil.copyfile(input_pdf, output_pdf)
        return True
    except Exception as exc:
        logger.error("Compression failed: %s", exc)
        return False
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


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
        doc = pymupdf.open(str(input_pdf))
        output_txt = _as_path(output_txt) if output_txt is not None else input_pdf.with_suffix(".txt")
        _ensure_parent_dir(output_txt)

        with open(output_txt, "w", encoding="utf-8") as f:
            for page in doc:
                f.write(page.get_text("text"))

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
        reader = PdfReader(str(input_pdf))
        return len(reader.pages)
    except FileNotDecryptedError:
        logger.warning("PDF is password-protected; page count needs the password: %s", input_pdf)
        return None
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
        reader = PdfReader(str(input_pdf))
        return bool(reader.is_encrypted)
    except Exception as exc:
        logger.error("Failed to read PDF: %s", exc)
        return None


def encrypt_pdf(input_pdf: str | Path, output_pdf: str | Path, password: str) -> Path | None:
    """Encrypt a PDF with a user password.

    Args:
        input_pdf: Input PDF.
        output_pdf: Output PDF.
        password: Password.

    Returns:
        Output path on success, otherwise None.
    """
    input_pdf = _as_path(input_pdf)
    output_pdf = _as_path(output_pdf)
    if not input_pdf.exists():
        logger.error("Input PDF not found: %s", input_pdf)
        return None

    try:
        reader = PdfReader(str(input_pdf))
        # Clone (not add_page) so bookmarks, form fields and metadata are kept.
        writer = PdfWriter(clone_from=reader)

        # pypdf defaults to RC4-128, which is broken; AES-256 uses `cryptography`.
        writer.encrypt(password, algorithm="AES-256")

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
    password: str,
) -> Path | None:
    """Decrypt an encrypted PDF and write an unencrypted copy.

    Args:
        input_pdf: Input PDF.
        output_pdf: Output PDF.
        password: Password.

    Returns:
        Output path on success, otherwise None.
    """
    input_pdf = _as_path(input_pdf)
    output_pdf = _as_path(output_pdf)
    if not input_pdf.exists():
        logger.error("Input PDF not found: %s", input_pdf)
        return None

    try:
        reader = PdfReader(str(input_pdf))
        if reader.is_encrypted:
            ok = reader.decrypt(password)
            if not ok:
                logger.error("Incorrect password or unable to decrypt.")
                return None

        # Clone (not add_page) so bookmarks, form fields and metadata are kept.
        writer = PdfWriter(clone_from=reader)

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
        reader = PdfReader(str(input_pdf))
        # Clone (not add_page) so bookmarks, form fields and metadata are kept.
        writer = PdfWriter(clone_from=reader)
        selected: set[int] | None = None
        if pages:
            selected = set(_parse_page_selection(pages, total_pages=len(reader.pages)))

        for idx, page in enumerate(writer.pages):
            if selected is None or idx in selected:
                page.rotate(angle)

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
        reader = PdfReader(str(input_pdf))
        to_delete = set(_parse_page_selection(pages, total_pages=len(reader.pages)))
        kept = [idx for idx in range(len(reader.pages)) if idx not in to_delete]
        if not kept:
            logger.error("Refusing to delete every page (%s): the output would be an empty PDF.", pages)
            return False

        writer = PdfWriter()
        # append() keeps bookmarks and form fields that point at kept pages.
        writer.append(reader, pages=kept)
        if reader.metadata:
            writer.add_metadata(reader.metadata)

        _ensure_parent_dir(output_pdf)
        with open(output_pdf, "wb") as f:
            writer.write(f)
        logger.info("Deleted pages (%s). Kept %d pages -> %s", pages, len(kept), output_pdf)
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
        reader = PdfReader(str(input_pdf))
        total = len(reader.pages)
        indices = [i - 1 for i in order]
        if any(i < 0 or i >= total for i in indices):
            logger.error("Order contains out-of-range page numbers (1..%d)", total)
            return False

        writer = PdfWriter()
        # append() keeps bookmarks and form fields that point at included pages.
        writer.append(reader, pages=indices)
        if reader.metadata:
            writer.add_metadata(reader.metadata)

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
        doc = _open_pdf_for_edit(input_pdf)
        pages = int(doc.page_count)
        # Placeholders only add digits, so the templates decide the font.
        font_kwargs, _ = _pick_font(pymupdf, (header or "") + (footer or ""))
        for page_no in range(1, pages + 1):
            page = doc.load_page(page_no - 1)
            rect = page.rect
            if header:
                page.insert_text(
                    (margin, margin),
                    _fill_page_placeholders(header, page=page_no, pages=pages),
                    fontsize=fontsize,
                    **font_kwargs,
                )
            if footer:
                page.insert_text(
                    (margin, rect.height - margin),
                    _fill_page_placeholders(footer, page=page_no, pages=pages),
                    fontsize=fontsize,
                    **font_kwargs,
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
    rotate: float = 45,
    opacity: float = 0.15,
) -> bool:
    """Apply a text watermark across each page using PyMuPDF.

    Args:
        input_pdf: Input PDF.
        output_pdf: Output PDF.
        text: Watermark text.
        fontsize: Font size.
        rotate: Rotation angle in degrees (any value, counter-clockwise).
        opacity: Opacity (0..1).

    Returns:
        True if successful, otherwise False.
    """
    input_pdf = _as_path(input_pdf)
    output_pdf = _as_path(output_pdf)
    if not input_pdf.exists():
        logger.error("Input PDF not found: %s", input_pdf)
        return False
    if not 0 <= opacity <= 1:
        logger.error("opacity must be between 0 and 1")
        return False

    try:
        doc = _open_pdf_for_edit(input_pdf)
        pages = int(doc.page_count)
        font_kwargs, font = _pick_font(pymupdf, text)
        text_width = font.text_length(text, fontsize=fontsize)
        for page_index in range(pages):
            page = doc.load_page(page_index)
            rect = page.rect
            center = pymupdf.Point(rect.width / 2, rect.height / 2)
            # Start the baseline so the text is centred, then rotate around the
            # centre via `morph`: insert_text's own `rotate` only accepts
            # multiples of 90 and raises "bad rotate value" otherwise.
            start = pymupdf.Point(center.x - text_width / 2, center.y + fontsize / 3)
            page.insert_text(
                start,
                text,
                fontsize=fontsize,
                color=(0.6, 0.6, 0.6),
                fill_opacity=opacity,
                morph=(center, pymupdf.Matrix(rotate)),
                **font_kwargs,
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
        src = _open_pdf_for_edit(input_pdf)
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
        reader = PdfReader(str(input_pdf))
        # Clone so existing metadata (and bookmarks/forms) are kept;
        # add_metadata then only overrides the given keys.
        writer = PdfWriter(clone_from=reader)
        writer.add_metadata(metadata)

        _ensure_parent_dir(output_pdf)
        with open(output_pdf, "wb") as f:
            writer.write(f)
        logger.info("Metadata updated -> %s", output_pdf)
        return True
    except Exception as exc:
        logger.error("Metadata update failed: %s", exc)
        return False


def insert_pages_pdf(
    input_pdf: str | Path,
    output_pdf: str | Path,
    *,
    after: int,
    source_pdf: str | Path | None = None,
    source_pages: str | None = None,
    blank_count: int = 1,
) -> bool:
    """Insert blank pages, or pages from another PDF, at a chosen position.

    Args:
        input_pdf: Input PDF.
        output_pdf: Output PDF.
        after: Insert after this page (1-based); 0 inserts before the first page.
        source_pdf: PDF to take pages from. If None, blank pages are inserted.
        source_pages: Page selection in source_pdf, e.g. "1-3,6". None = all pages.
        blank_count: Number of blank pages (when source_pdf is None). Blank
            pages get the size of the page they follow (or of page 1).

    Returns:
        True if successful, otherwise False.
    """
    input_pdf = _as_path(input_pdf)
    output_pdf = _as_path(output_pdf)
    if not input_pdf.exists():
        logger.error("Input PDF not found: %s", input_pdf)
        return False
    if source_pdf is not None and not _as_path(source_pdf).exists():
        logger.error("PDF to insert not found: %s", source_pdf)
        return False
    if source_pdf is None and blank_count <= 0:
        logger.error("Number of blank pages must be at least 1")
        return False

    try:
        # Clone (not add_page) so bookmarks, form fields and metadata are kept.
        writer = PdfWriter(clone_from=PdfReader(str(input_pdf)))
        total = len(writer.pages)
        if not 0 <= after <= total:
            logger.error("Position must be between 0 and %d (the number of pages)", total)
            return False

        if source_pdf is None:
            box = writer.pages[max(after, 1) - 1].mediabox
            for _ in range(blank_count):
                writer.insert_blank_page(float(box.width), float(box.height), index=after)
            what = f"{blank_count} blank page(s)"
        else:
            source = PdfReader(str(source_pdf))
            if source_pages:
                indices = _parse_page_selection(source_pages, total_pages=len(source.pages))
            else:
                indices = list(range(len(source.pages)))
            writer.merge(after, source, pages=indices, import_outline=False)
            what = f"{len(indices)} page(s) from {_as_path(source_pdf).name}"

        _ensure_parent_dir(output_pdf)
        with open(output_pdf, "wb") as f:
            writer.write(f)
        logger.info("Inserted %s after page %d -> %s", what, after, output_pdf)
        return True
    except ValueError as exc:
        logger.error("Invalid page selection: %s", exc)
        return False
    except Exception as exc:
        logger.error("Insert pages failed: %s", exc)
        return False


def get_bookmarks(input_pdf: str | Path) -> list[tuple[int, str, int]] | None:
    """Return a PDF's bookmarks as (level, title, page) tuples (level and page 1-based).

    Bookmarks that point nowhere have page <= 0.
    """
    input_pdf = _as_path(input_pdf)
    if not input_pdf.exists():
        logger.error("Input PDF not found: %s", input_pdf)
        return None

    try:
        with pymupdf.open(str(input_pdf)) as doc:
            return [(int(level), str(title), int(page)) for level, title, page, *_ in doc.get_toc()]
    except Exception as exc:
        logger.error("Reading bookmarks failed: %s", exc)
        return None


def show_bookmarks(input_pdf: str | Path) -> bool:
    """Log a PDF's bookmarks as an indented list."""
    bookmarks = get_bookmarks(input_pdf)
    if bookmarks is None:
        return False
    if not bookmarks:
        logger.info("This PDF has no bookmarks.")
    for level, title, page in bookmarks:
        logger.info("%s%s (page %s)", "  " * (level - 1), title, page if page > 0 else "none")
    return True


def add_bookmark(input_pdf: str | Path, output_pdf: str | Path, title: str, page: int) -> bool:
    """Add a top-level bookmark, keeping top-level bookmarks in page order.

    Args:
        input_pdf: Input PDF.
        output_pdf: Output PDF.
        title: Bookmark title.
        page: Page the bookmark opens (1-based).

    Returns:
        True if successful, otherwise False.
    """
    input_pdf = _as_path(input_pdf)
    output_pdf = _as_path(output_pdf)
    if not title.strip():
        logger.error("The bookmark title cannot be empty")
        return False
    bookmarks = get_bookmarks(input_pdf)
    if bookmarks is None:
        return False

    try:
        total = pdf_page_count(input_pdf)
        if total is None:
            return False
        if not 1 <= page <= total:
            logger.error("Page must be between 1 and %d", total)
            return False

        toc = [list(b) for b in bookmarks]
        # Insert before the first top-level bookmark on a later page, so the
        # new one lands in reading order together with its predecessor's children.
        pos = next((i for i, (level, _, p) in enumerate(toc) if level == 1 and p > page), len(toc))
        toc.insert(pos, [1, title.strip(), page])
        with _open_pdf_for_edit(input_pdf) as doc:
            doc.set_toc(toc)
            _ensure_parent_dir(output_pdf)
            doc.save(str(output_pdf), garbage=1)
        logger.info("Added bookmark %r -> page %d -> %s", title.strip(), page, output_pdf)
        return True
    except Exception as exc:
        logger.error("Adding bookmark failed: %s", exc)
        return False


def redact_text_pdf(input_pdf: str | Path, output_pdf: str | Path, terms: Sequence[str]) -> int | None:
    """Permanently remove every occurrence of some text, leaving black boxes.

    Unlike drawing a box over text, the text itself is deleted from the
    page, so it cannot be copied, searched or recovered. Images under the
    boxes are blanked too. Matching ignores upper/lower case.

    Args:
        input_pdf: Input PDF.
        output_pdf: Output PDF.
        terms: Words or phrases to remove.

    Returns:
        Number of areas removed, or None on failure or when nothing matched
        (then no output is written).
    """
    input_pdf = _as_path(input_pdf)
    output_pdf = _as_path(output_pdf)
    terms = [t.strip() for t in terms if t and t.strip()]
    if not input_pdf.exists():
        logger.error("Input PDF not found: %s", input_pdf)
        return None
    if not terms:
        logger.error("Enter the text to remove")
        return None

    try:
        with _open_pdf_for_edit(input_pdf) as doc:
            count = 0
            no_text_pages: list[int] = []
            for page in doc:
                if not page.get_text("text").strip():
                    # Only pages with pictures can hide text; blank pages can't.
                    if page.get_images():
                        no_text_pages.append(page.number + 1)
                    continue
                for term in terms:
                    for rect in page.search_for(term):
                        page.add_redact_annot(rect, fill=(0, 0, 0))
                        count += 1
                page.apply_redactions()

            if no_text_pages:
                logger.warning(
                    "Pages with no text layer (scanned?) were skipped: %s. "
                    "Text inside images can't be found; run OCR first.",
                    ", ".join(map(str, no_text_pages)),
                )
            if count == 0:
                logger.error("None of the text was found, so nothing was written.")
                return None

            leftover = [t for t in terms for page in doc if t.lower() in page.get_text("text").lower()]
            if leftover:
                logger.warning(
                    "Some text could still be found after redaction (e.g. split across lines): %s",
                    ", ".join(sorted(set(leftover))),
                )
            # Text in the document details or bookmarks is not on a page, so
            # redaction does not reach it; point it out instead of hiding it.
            hidden_places = [str(v) for v in (doc.metadata or {}).values() if v] + [
                str(entry[1]) for entry in doc.get_toc()
            ]
            if any(t.lower() in v.lower() for t in terms for v in hidden_places):
                logger.warning(
                    "The text also appears in the document details or bookmarks, which "
                    "redaction does not change. Check them with options 17 and 25."
                )

            _ensure_parent_dir(output_pdf)
            # garbage=4 drops the replaced page content so it isn't left in the file.
            doc.save(str(output_pdf), garbage=4, deflate=True)
        logger.info("Redacted %d area(s) -> %s", count, output_pdf)
        return count
    except Exception as exc:
        logger.error("Redaction failed: %s", exc)
        return None


def convert_to_pdfa(input_pdf: str | Path, output_pdf: str | Path, *, ocr: bool = False) -> bool:
    """Convert a PDF to PDF/A-2b, the standard for long-term archiving.

    Args:
        input_pdf: Input PDF.
        output_pdf: Output PDF/A.
        ocr: Also make pages without text searchable (OCR). Pages that already
            have text are never OCRed.

    Returns:
        True if successful, otherwise False.

    Notes:
        Uses `ocrmypdf`, which needs Tesseract and Ghostscript installed even
        when ocr is False.
    """
    input_pdf = _as_path(input_pdf)
    output_pdf = _as_path(output_pdf)
    if not input_pdf.exists():
        logger.error("Input PDF not found: %s", input_pdf)
        return False

    try:
        import ocrmypdf
        from ocrmypdf.exceptions import EncryptedPdfError, MissingDependencyError
    except ModuleNotFoundError:
        logger.error("Missing dependency: ocrmypdf (install with `pip install ocrmypdf`)")
        return False

    kwargs: dict[str, object] = {"output_type": "pdfa", "skip_text": True}
    if not ocr:
        # A zero timeout makes ocrmypdf skip OCR entirely.
        kwargs["tesseract_timeout"] = 0
    try:
        _ensure_parent_dir(output_pdf)
        result = ocrmypdf.ocr(str(input_pdf), str(output_pdf), **kwargs)
        if result != ocrmypdf.ExitCode.ok:
            logger.error("PDF/A conversion failed with exit code %s", getattr(result, "name", result))
            return False
        logger.info("Saved as PDF/A -> %s", output_pdf)
        return True
    except MissingDependencyError as exc:
        logger.error(
            "PDF/A needs Tesseract and Ghostscript installed (menu option 23 checks): %s", exc
        )
        return False
    except EncryptedPdfError:
        logger.error("The PDF is password-protected. Remove the password first (option 9).")
        return False
    except Exception as exc:
        logger.error("PDF/A conversion failed: %s", exc)
        return False


# Batch operations: output filename suffix, the function that runs it, and
# the extra options it accepts (passed through as keyword arguments).
_BATCH_OPERATIONS: dict[str, tuple[str, Callable[..., object], tuple[str, ...]]] = {
    "ocr": ("_ocr.pdf", ocr_pdf, ("language",)),
    "compress": ("_compressed.pdf", compress_pdf, ()),
    "extract-text": (".txt", extract_text_from_pdf, ()),
    "watermark": ("_watermarked.pdf", watermark_pdf, ("text", "fontsize", "rotate", "opacity")),
    "rotate": ("_rotated.pdf", rotate_pdf, ("angle", "pages")),
    "header-footer": ("_header_footer.pdf", add_header_footer_pdf, ("header", "footer", "margin", "fontsize")),
}


class BatchResult(NamedTuple):
    """Outcome of batch_process_folder."""

    succeeded: int
    total: int

    @property
    def all_succeeded(self) -> bool:
        """True when files matched and every one of them was processed."""
        return self.total > 0 and self.succeeded == self.total


def batch_process_folder(
    folder: str | Path,
    *,
    glob_pattern: str = "*.pdf",
    operation: str,
    output_dir: str | Path | None = None,
    language: str = "eng",
    **options: object,
) -> BatchResult:
    """Run an operation on all PDFs in a folder.

    Supported operations and their options:
        - "ocr": language
        - "compress"
        - "extract-text"
        - "watermark": text (required), fontsize, rotate, opacity
        - "rotate": angle (required, a multiple of 90), pages
        - "header-footer": header and/or footer (one required), margin, fontsize

    Each output is named after its input plus a suffix, e.g. "a_rotated.pdf".

    Args:
        folder: Folder containing PDFs.
        glob_pattern: Glob pattern to match PDFs.
        operation: Operation name.
        output_dir: Where outputs are written. If None, uses folder.
        language: OCR language (for operation="ocr").
        **options: Options for the operation (see above). None values are
            ignored, so callers can pass every option and let each operation
            use its own defaults.

    Returns:
        How many files succeeded out of how many matched. Both are 0 when
        the request is rejected before any file is processed.
    """
    folder = _as_path(folder)
    if output_dir is None:
        output_dir = folder
    output_dir = _as_path(output_dir)
    if not folder.exists():
        logger.error("Folder not found: %s", folder)
        return BatchResult(0, 0)
    if operation not in _BATCH_OPERATIONS:
        logger.error(
            "Unknown batch operation: %s (choose from %s)", operation, ", ".join(_BATCH_OPERATIONS)
        )
        return BatchResult(0, 0)

    suffix, func, allowed = _BATCH_OPERATIONS[operation]
    given = {k: v for k, v in {"language": language, **options}.items() if v is not None}
    kwargs = {k: v for k, v in given.items() if k in allowed}
    ignored = sorted(k for k in given if k not in allowed and k != "language")
    if ignored:
        logger.warning("Options not used by %s: %s", operation, ", ".join(ignored))

    # Check required options once, instead of failing on every file.
    if operation == "watermark" and not kwargs.get("text"):
        logger.error("Batch watermark needs the watermark text")
        return BatchResult(0, 0)
    if operation == "rotate":
        angle = kwargs.get("angle")
        if not isinstance(angle, int) or angle % 90 != 0:
            logger.error("Batch rotate needs an angle that is a multiple of 90 (got %r)", angle)
            return BatchResult(0, 0)
    if operation == "header-footer" and not (kwargs.get("header") or kwargs.get("footer")):
        logger.error("Batch header-footer needs a header, a footer, or both")
        return BatchResult(0, 0)

    pdfs = sorted(folder.glob(glob_pattern))
    # When results are saved next to the originals, an earlier run's results
    # (e.g. "a_rotated.pdf") match too; processing them again would create
    # "a_rotated_rotated.pdf".
    if output_dir.resolve() == folder.resolve():
        earlier = [p for p in pdfs if p.name.lower().endswith(suffix.lower())]
        if earlier:
            logger.info("Skipping %d result(s) of an earlier %s run", len(earlier), operation)
            pdfs = [p for p in pdfs if p not in earlier]
    if not pdfs:
        logger.error("No PDFs matched %s in %s", glob_pattern, folder)
        return BatchResult(0, 0)

    failed: list[str] = []
    for pdf in pdfs:
        out = output_dir / f"{pdf.stem}{suffix}"
        result = func(pdf, out, **kwargs)
        # Most operations return a bool; extract-text returns a path or None.
        if result is None or result is False:
            failed.append(pdf.name)

    ok = len(pdfs) - len(failed)
    if failed:
        logger.error(
            "Batch finished with problems: %d of %d files failed: %s",
            len(failed),
            len(pdfs),
            ", ".join(failed),
        )
    else:
        logger.info("Batch complete: %d/%d succeeded", ok, len(pdfs))
    return BatchResult(ok, len(pdfs))


def _parse_order(value: str) -> list[int]:
    """Parse a comma-separated list of integers.

    Raises:
        ValueError: If an item is not an integer or the list is empty.
    """
    order = [int(x.strip()) for x in value.split(",") if x.strip()]
    if not order:
        raise ValueError("empty page order")
    return order


def _show_pdf_info(input_pdf: str | Path) -> int:
    """Log page count and encryption status; return a process exit code."""
    enc = pdf_is_encrypted(input_pdf)
    if enc is None:
        return 1
    pages = pdf_page_count(input_pdf)
    if pages is None and not enc:
        return 1
    logger.info("Pages: %s", pages if pages is not None else "unknown (password required)")
    logger.info("Encrypted: %s", enc)
    return 0


def _parse_page_selection(selection: str, *, total_pages: int, clamp_end: bool = False) -> list[int]:
    """Parse a page selection string like "1-3,6,10" (1-based, inclusive).

    Returns a list of 0-based page indices in the order specified, with duplicates removed.

    Args:
        selection: Comma-separated pages and ranges (e.g. "9,10,17-115").
        total_pages: Total number of pages in the PDF.
        clamp_end: Cut a range's end down to the last page instead of raising.

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
            if clamp_end and start <= total_pages < end:
                logger.warning("Range '%s' ends past the last page; using %d-%d", part, start, total_pages)
                end = total_pages
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


# Packages loaded only by the features that use them (PyMuPDF and pypdf load at start-up).
_FEATURE_PACKAGES = ("pikepdf", "img2pdf", "pdf2docx", "ocrmypdf")


def check_setup() -> int:
    """Print which features are ready and what is missing for the rest.

    Returns:
        1 if Python packages are missing (setup did not finish), otherwise 0.
        Missing optional programs only produce warnings.
    """
    import importlib.util

    # Printed (not logged) so the report shows at any --log-level.
    def report(status: str, message: str) -> None:
        print(f"[{status:^4}] {message}")

    print("\nJAP-T setup check")
    rc = 0
    report("OK", f"Python {sys.version.split()[0]}")

    missing = [name for name in _FEATURE_PACKAGES if importlib.util.find_spec(name) is None]
    if missing:
        report("FAIL", f"Missing Python packages: {', '.join(missing)}. Run setupEnv.bat again.")
        rc = 1
    else:
        report("OK", "Python packages")

    tesseract = _find_tesseract()
    if tesseract:
        report("OK", f"Tesseract OCR: {tesseract}")
    else:
        report(
            "WARN",
            "Tesseract OCR not found. OCR (options 2 and 20) and PDF/A (option 27) will not work. "
            "Get it from https://github.com/UB-Mannheim/tesseract/wiki",
        )

    gs = _find_ghostscript()
    if gs:
        report("OK", f"Ghostscript: {gs}")
    else:
        report(
            "WARN",
            "Ghostscript not found. OCR and PDF/A will not work, and Compress saves less. "
            "Get it from https://ghostscript.com/releases/gsdnld.html",
        )

    word = _word_installed() and importlib.util.find_spec("docx2pdf") is not None
    soffice = _find_soffice()
    if word:
        report("OK", "DOCX -> PDF: Microsoft Word")
    if soffice:
        report("OK", f"DOCX -> PDF: LibreOffice ({soffice})")
    if not word and not soffice:
        report(
            "WARN",
            "DOCX -> PDF (option 22) needs Microsoft Word or LibreOffice; neither was found. "
            "Get LibreOffice free from https://www.libreoffice.org/download/",
        )

    return rc


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(prog="pdfsuite", description="Small PDF utility suite")
    parser.add_argument("--log-level", default="INFO", help="DEBUG|INFO|WARNING|ERROR")

    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("menu", help="Interactive menu runner")
    sub.add_parser("check", help="Check which features are ready and what is missing")

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

    # "jpg-merge" is the older name, kept so existing scripts keep working.
    p = sub.add_parser(
        "images-to-pdf",
        aliases=["jpg-merge"],
        help="Combine images (JPG, PNG, TIFF, BMP, GIF, WebP) into a PDF",
    )
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
    p.add_argument("--password", default=None, help="Password. Omit it to be asked without the password showing on screen (a password typed here can be saved in your command history).")

    p = sub.add_parser("decrypt", help="Decrypt PDF")
    p.add_argument("--in", dest="input_pdf", required=True)
    p.add_argument("--out", dest="output_pdf", required=True)
    p.add_argument("--password", default=None, help="Password. Omit it to be asked without the password showing on screen (a password typed here can be saved in your command history).")

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

    p = sub.add_parser("insert-pages", help="Insert blank pages or pages from another PDF")
    p.add_argument("--in", dest="input_pdf", required=True)
    p.add_argument("--out", dest="output_pdf", required=True)
    p.add_argument("--after", type=int, required=True, help="Insert after this page (0 = before page 1)")
    p.add_argument("--from", dest="source_pdf", default=None, help="PDF to take pages from (default: blank pages)")
    p.add_argument("--pages", dest="source_pages", default=None, help='Pages of --from to insert, e.g. "1-3"; default all')
    p.add_argument("--blank", dest="blank_count", type=int, default=1, help="Number of blank pages (without --from)")

    p = sub.add_parser("bookmarks-show", help="List a PDF's bookmarks")
    p.add_argument("--in", dest="input_pdf", required=True)

    p = sub.add_parser("bookmarks-add", help="Add a bookmark")
    p.add_argument("--in", dest="input_pdf", required=True)
    p.add_argument("--out", dest="output_pdf", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--page", type=int, required=True)

    p = sub.add_parser("redact", help="Permanently remove text")
    p.add_argument("--in", dest="input_pdf", required=True)
    p.add_argument("--out", dest="output_pdf", required=True)
    p.add_argument("--text", dest="terms", action="append", required=True, help="Text to remove; repeat for more")

    p = sub.add_parser("pdfa", help="Save as PDF/A for long-term archiving")
    p.add_argument("--in", dest="input_pdf", required=True)
    p.add_argument("--out", dest="output_pdf", required=True)
    p.add_argument("--ocr", action="store_true", help="Also make scanned pages searchable")

    p = sub.add_parser("batch", help="Batch process a folder")
    p.add_argument("--folder", required=True)
    p.add_argument("--op", required=True, choices=list(_BATCH_OPERATIONS))
    p.add_argument("--glob", dest="glob_pattern", default="*.pdf")
    p.add_argument("--out-dir", dest="output_dir", default=None)
    p.add_argument("--lang", default="eng", help="OCR language (ocr)")
    # Defaults are None so each operation falls back to its own defaults.
    p.add_argument("--text", default=None, help="Watermark text (watermark)")
    p.add_argument("--rotate", type=float, default=None, help="Watermark angle in degrees (watermark)")
    p.add_argument("--opacity", type=float, default=None, help="Watermark opacity 0..1 (watermark)")
    p.add_argument("--angle", type=int, default=None, help="Rotation: 90, 180 or 270 (rotate)")
    p.add_argument("--pages", default=None, help='Pages to rotate, e.g. "1-3,6"; default all (rotate)')
    p.add_argument("--header", default=None, help="Header text, supports {page}/{pages} (header-footer)")
    p.add_argument("--footer", default=None, help="Footer text, supports {page}/{pages} (header-footer)")
    p.add_argument("--margin", type=float, default=None, help="Margin in points (header-footer)")
    p.add_argument("--fontsize", type=float, default=None, help="Font size (watermark, header-footer)")

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


def _prompt_password(*, new: bool = False) -> str:
    """Ask for a password without showing it on screen.

    Args:
        new: True when setting a password. It must not be empty and is
            asked twice so a typo cannot lock the file.
    """
    while True:
        pw = getpass.getpass("Password (hidden as you type): ")
        if not new:
            return pw
        if not pw:
            logger.error("The password cannot be empty.")
            continue
        if getpass.getpass("Type the password again: ") != pw:
            logger.error("The passwords do not match. Try again.")
            continue
        return pw


def _strip_quotes(value: str) -> str:
    """Remove one pair of matching quotes around a value.

    Windows "Copy as path" wraps paths in double quotes.
    """
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1].strip()
    return value


def _prompt_path(value_name: str, *, default: str | None = None) -> str:
    """Prompt for a file or folder path, ignoring surrounding quotes."""
    return _strip_quotes(_prompt(value_name, default=default))


def _prompt_path_list(value_name: str, *, default: str | None = None) -> list[str]:
    """Prompt for a comma-separated list of paths, ignoring quotes around each one.

    A path in double quotes (as "Copy as path" gives) may itself contain commas.
    """
    raw = _prompt(value_name, default=default)
    items = next(csv.reader([raw], skipinitialspace=True), [])
    return [_strip_quotes(x.strip()) for x in items if x.strip()]


def _prompt_output(
    value_name: str,
    *,
    inputs: Sequence[str] = (),
    default: str | None = None,
    base_dir: str | None = None,
) -> str:
    """Prompt for an output file path.

    Re-asks when the path is blank, is one of the input files, or names an
    existing file the user does not want to overwrite.

    Args:
        value_name: Label shown to the user.
        inputs: Input paths the output must not replace.
        default: Optional default returned when user enters blank input.
        base_dir: Folder a relative output path is resolved against, when the
            operation writes relative outputs somewhere other than the
            current directory.
    """
    while True:
        out = _prompt_path(value_name, default=default)
        if not out:
            if default is not None:
                return out
            logger.error("Please enter a file name.")
            continue
        out_path = Path(out)
        if base_dir and not out_path.is_absolute():
            out_path = Path(base_dir) / out_path
        if out_path.exists():
            if any(Path(i).exists() and os.path.samefile(out_path, i) for i in inputs if i):
                logger.error("The output must be a different file from the input. Choose another name.")
                continue
            if out_path.is_dir():
                logger.error("%s is a folder. Enter a file name.", out_path)
                continue
            if not _prompt(f"{out_path} already exists. Overwrite? (y/n)", default="n").lower().startswith("y"):
                continue
        return out


# Menu entries in display order: (choice, label).
_MENU_ITEMS = (
    ("1", "PDF -> DOCX"),
    ("2", "OCR PDF"),
    ("3", "Merge PDFs"),
    ("4", "Split PDF"),
    ("5", "Images (JPG/PNG/...) -> PDF"),
    ("6", "Compress PDF"),
    ("7", "Extract text"),
    ("8", "Encrypt PDF"),
    ("9", "Decrypt PDF"),
    ("10", "Rotate pages"),
    ("11", "Delete pages"),
    ("12", "Reorder pages"),
    ("13", "Add header/footer"),
    ("14", "Watermark"),
    ("15", "Extract images"),
    ("16", "PDF -> images"),
    ("17", "Show metadata"),
    ("18", "Set metadata"),
    ("19", "PDF info (pages/encrypted)"),
    ("20", "Batch folder"),
    ("21", "Convert selected pages to non-OCR"),
    ("22", "DOCX -> PDF"),
    ("23", "Check setup"),
    ("24", "Insert pages"),
    ("25", "Bookmarks (show/add)"),
    ("26", "Redact (permanently remove) text"),
    ("27", "Save as PDF/A (archiving)"),
    ("0", "Exit"),
)


def interactive_menu() -> int:
    """Run the interactive menu until the user chooses Exit.

    After each job the menu is shown again.

    Returns:
        Process exit code (0 when the user exits from the menu).
    """
    while True:
        # Menu text goes to stdout so it stays visible at any --log-level.
        print("\nPDFSuite Menu")
        for number, label in _MENU_ITEMS:
            print(f"{number}) {label}")

        try:
            choice = _prompt("Choose", default="0")
        except (KeyboardInterrupt, EOFError):
            print()
            return 0
        if choice in {"0", "q", "quit", "exit"}:
            return 0

        try:
            rc = _run_menu_choice(choice)
        except KeyboardInterrupt:
            print("\nCancelled.")
            continue
        except EOFError:
            print()
            return 1
        if rc is None:
            continue

        print("\nDone." if rc == 0 else "\nFailed. See the messages above.")
        try:
            input("Press Enter to return to the menu...")
        except (KeyboardInterrupt, EOFError):
            print()
            return 0


def _run_menu_choice(choice: str) -> int | None:
    """Ask for the inputs of one menu job and run it.

    Returns:
        0 on success, 1 on failure, or None for an unknown choice.
    """
    if choice == "1":
        inp = _prompt_path("Input PDF")
        out = _prompt_output("Output DOCX", inputs=[inp])
        return 0 if pdf_to_docx(inp, out) else 1

    if choice == "22":
        inp = _prompt_path("Input DOCX")
        out = _prompt_output("Output PDF", inputs=[inp])
        return 0 if docx_to_pdf(inp, out) else 1

    if choice == "2":
        inp = _prompt_path("Input PDF")
        out = _prompt_output("Output PDF", inputs=[inp])
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
        inputs = _prompt_path_list("Input PDFs (comma-separated)")
        out = _prompt_output("Output merged PDF", inputs=inputs)
        return 0 if merge_pdfs(inputs, out) else 1

    if choice == "4":
        inp = _prompt_path("Input PDF")
        mode = _prompt("Mode (single/range/chunk)", default="single").strip().lower()
        out_dir = _prompt_path("Output directory", default=".")
        prefix = _prompt("Filename prefix (optional)", default="")
        pr = _prompt("Page range (for mode=range)", default="1-10")
        chunk = _prompt_int("Chunk size (for mode=chunk)", default=10)
        ok = split_pdf(inp, mode=mode, page_range=pr, chunk_size=chunk, output_dir=out_dir, prefix=prefix)
        return 0 if ok else 1

    if choice == "5":
        folder = _prompt_path("Image folder")
        out = _prompt_output("Output PDF", default="merged_output.pdf", base_dir=folder)
        files = _prompt_path_list("Filenames (comma-separated, optional)", default="") or None
        return 0 if images_to_pdf(folder, files, out) else 1

    if choice == "6":
        inp = _prompt_path("Input PDF")
        out = _prompt_output("Output PDF", inputs=[inp])
        return 0 if compress_pdf(inp, out) else 1

    if choice == "7":
        inp = _prompt_path("Input PDF")
        # Same default as extract_text_from_pdf, shown so the overwrite check covers it.
        default_txt = str(Path(inp).with_suffix(".txt")) if inp else ""
        out = _prompt_output("Output TXT", inputs=[inp], default=default_txt)
        return 0 if extract_text_from_pdf(inp, out or None) is not None else 1

    if choice == "8":
        inp = _prompt_path("Input PDF")
        out = _prompt_output("Output encrypted PDF", inputs=[inp])
        pw = _prompt_password(new=True)
        return 0 if encrypt_pdf(inp, out, pw) is not None else 1

    if choice == "9":
        inp = _prompt_path("Input PDF")
        out = _prompt_output("Output decrypted PDF", inputs=[inp])
        pw = _prompt_password()
        return 0 if decrypt_pdf(inp, out, pw) is not None else 1

    if choice == "10":
        inp = _prompt_path("Input PDF")
        out = _prompt_output("Output PDF", inputs=[inp])
        angle = _prompt_int("Angle (90/180/270)", default=90)
        pages = _prompt("Pages (optional, e.g. 1-3,6)", default="")
        pages_val = pages if pages else None
        return 0 if rotate_pdf(inp, out, angle, pages=pages_val) else 1

    if choice == "11":
        inp = _prompt_path("Input PDF")
        out = _prompt_output("Output PDF", inputs=[inp])
        pages = _prompt("Pages to delete (e.g. 1-3,6)")
        return 0 if delete_pages_pdf(inp, out, pages) else 1

    if choice == "12":
        inp = _prompt_path("Input PDF")
        out = _prompt_output("Output PDF", inputs=[inp])
        order_raw = _prompt("New order (comma-separated, e.g. 2,1,3)")
        try:
            order = _parse_order(order_raw)
        except ValueError as exc:
            logger.error("Invalid order %r: %s", order_raw, exc)
            return 1
        return 0 if reorder_pages_pdf(inp, out, order) else 1

    if choice == "13":
        inp = _prompt_path("Input PDF")
        out = _prompt_output("Output PDF", inputs=[inp])
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
        inp = _prompt_path("Input PDF")
        out = _prompt_output("Output PDF", inputs=[inp])
        text = _prompt("Watermark text")
        fontsize = _prompt_float("Font size", default=48)
        rotate = _prompt_float("Rotate", default=45)
        opacity = _prompt_float("Opacity (0..1)", default=0.15)
        return 0 if watermark_pdf(inp, out, text, fontsize=fontsize, rotate=rotate, opacity=opacity) else 1

    if choice == "15":
        inp = _prompt_path("Input PDF")
        out_dir = _prompt_path("Output directory")
        return 0 if extract_images_from_pdf(inp, out_dir) is not None else 1

    if choice == "16":
        inp = _prompt_path("Input PDF")
        out_dir = _prompt_path("Output directory")
        dpi = _prompt_int("DPI", default=150)
        fmt = _prompt("Format (png/jpg)", default="png")
        return 0 if pdf_to_images(inp, out_dir, dpi=dpi, fmt=fmt) is not None else 1

    if choice == "17":
        inp = _prompt_path("Input PDF")
        return 0 if show_pdf_metadata(inp) is not None else 1

    if choice == "18":
        inp = _prompt_path("Input PDF")
        out = _prompt_output("Output PDF", inputs=[inp])
        raw = _prompt('Metadata JSON (e.g. {"/Title":"X"})')
        try:
            md = _parse_metadata_json(raw)
        except ValueError as exc:
            logger.error("Invalid JSON: %s", exc)
            return 1
        return 0 if set_pdf_metadata(inp, out, md) else 1

    if choice == "19":
        inp = _prompt_path("Input PDF")
        return _show_pdf_info(inp)

    if choice == "20":
        folder = _prompt_path("Folder")
        op = _prompt(f"Operation ({'/'.join(_BATCH_OPERATIONS)})").strip().lower()
        if op not in _BATCH_OPERATIONS:
            logger.error("Unknown batch operation: %s", op)
            return 1
        glob_pattern = _prompt("Glob", default="*.pdf")
        out_dir = _prompt_path("Output directory (optional)", default="")
        out_dir_val = out_dir if out_dir else None
        # Ask only the questions the chosen operation needs, with the same
        # defaults as the single-file menu options.
        options: dict[str, object] = {}
        if op == "ocr":
            options["language"] = _prompt("Language", default="eng")
        elif op == "watermark":
            options["text"] = _prompt("Watermark text")
            options["fontsize"] = _prompt_float("Font size", default=48)
            options["rotate"] = _prompt_float("Rotate", default=45)
            options["opacity"] = _prompt_float("Opacity (0..1)", default=0.15)
        elif op == "rotate":
            options["angle"] = _prompt_int("Angle (90/180/270)", default=90)
            options["pages"] = _prompt("Pages (optional, e.g. 1-3,6)", default="") or None
        elif op == "header-footer":
            options["header"] = _prompt('Header (optional, supports {page}/{pages})', default="") or None
            options["footer"] = _prompt('Footer (optional, supports {page}/{pages})', default="") or None
            options["margin"] = _prompt_float("Margin (points)", default=36)
            options["fontsize"] = _prompt_float("Font size", default=10)
        result = batch_process_folder(
            folder,
            glob_pattern=glob_pattern,
            operation=op,
            output_dir=out_dir_val,
            **options,
        )
        return 0 if result.all_succeeded else 1

    if choice == "21":
        inp = _prompt_path("Input PDF")
        out = _prompt_output("Output PDF", inputs=[inp])
        pages = _prompt('Pages to convert (e.g. 1,2,9-12,16)')
        dpi = _prompt_int("DPI", default=150)
        return 0 if deocr_selected_pages(inp, out, pages, dpi=dpi) else 1

    if choice == "23":
        return check_setup()

    if choice == "24":
        inp = _prompt_path("Input PDF")
        out = _prompt_output("Output PDF", inputs=[inp])
        after = _prompt_int("Insert after page (0 = before the first page)", default=0)
        if _prompt("Insert pages from another PDF? (y = another PDF, n = blank pages)", default="n").lower().startswith("y"):
            src = _prompt_path("PDF to take pages from")
            src_pages = _prompt("Pages to take (optional, e.g. 1-3,6; blank = all)", default="")
            ok = insert_pages_pdf(inp, out, after=after, source_pdf=src, source_pages=src_pages or None)
        else:
            count = _prompt_int("How many blank pages", default=1)
            ok = insert_pages_pdf(inp, out, after=after, blank_count=count)
        return 0 if ok else 1

    if choice == "25":
        action = _prompt("Action (show/add)", default="show").strip().lower()
        if action == "show":
            return 0 if show_bookmarks(_prompt_path("Input PDF")) else 1
        if action == "add":
            inp = _prompt_path("Input PDF")
            out = _prompt_output("Output PDF", inputs=[inp])
            title = _prompt("Bookmark title")
            page = _prompt_int("Page it opens")
            return 0 if add_bookmark(inp, out, title, page) else 1
        logger.error("Unknown action: %s", action)
        return 1

    if choice == "26":
        inp = _prompt_path("Input PDF")
        out = _prompt_output("Output PDF", inputs=[inp])
        raw = _prompt("Text to remove (separate several with |)")
        terms = [t.strip() for t in raw.split("|") if t.strip()]
        return 0 if redact_text_pdf(inp, out, terms) is not None else 1

    if choice == "27":
        inp = _prompt_path("Input PDF")
        out = _prompt_output("Output PDF/A", inputs=[inp])
        ocr = _prompt("Also make scanned pages searchable (OCR)? (y/n)", default="n").lower().startswith("y")
        return 0 if convert_to_pdfa(inp, out, ocr=ocr) else 1

    logger.error("Unknown choice: %s", choice)
    return None



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
    if cmd == "check":
        return check_setup()
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

    if cmd in ("images-to-pdf", "jpg-merge"):
        return 0 if images_to_pdf(args.folder, args.files, args.output_pdf) else 1

    if cmd == "compress":
        return 0 if compress_pdf(args.input_pdf, args.output_pdf) else 1

    if cmd == "extract-text":
        out = extract_text_from_pdf(args.input_pdf, args.output_txt)
        return 0 if out is not None else 1

    if cmd == "encrypt":
        try:
            password = args.password if args.password is not None else _prompt_password(new=True)
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled.")
            return 1
        out = encrypt_pdf(args.input_pdf, args.output_pdf, password)
        return 0 if out is not None else 1

    if cmd == "decrypt":
        try:
            password = args.password if args.password is not None else _prompt_password()
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled.")
            return 1
        out = decrypt_pdf(args.input_pdf, args.output_pdf, password)
        return 0 if out is not None else 1

    if cmd == "rotate":
        return 0 if rotate_pdf(args.input_pdf, args.output_pdf, args.angle, pages=args.pages) else 1

    if cmd == "delete-pages":
        return 0 if delete_pages_pdf(args.input_pdf, args.output_pdf, args.pages) else 1

    if cmd == "reorder":
        try:
            order = _parse_order(args.order)
        except ValueError as exc:
            logger.error("Invalid --order value %r: %s", args.order, exc)
            return 1
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
            md = _parse_metadata_json(args.json_metadata)
        except ValueError as exc:
            logger.error("Invalid --json value: %s", exc)
            return 1
        return 0 if set_pdf_metadata(args.input_pdf, args.output_pdf, md) else 1

    if cmd == "info":
        return _show_pdf_info(args.input_pdf)

    if cmd == "insert-pages":
        ok = insert_pages_pdf(
            args.input_pdf,
            args.output_pdf,
            after=args.after,
            source_pdf=args.source_pdf,
            source_pages=args.source_pages,
            blank_count=args.blank_count,
        )
        return 0 if ok else 1

    if cmd == "bookmarks-show":
        return 0 if show_bookmarks(args.input_pdf) else 1

    if cmd == "bookmarks-add":
        return 0 if add_bookmark(args.input_pdf, args.output_pdf, args.title, args.page) else 1

    if cmd == "redact":
        return 0 if redact_text_pdf(args.input_pdf, args.output_pdf, args.terms) is not None else 1

    if cmd == "pdfa":
        return 0 if convert_to_pdfa(args.input_pdf, args.output_pdf, ocr=args.ocr) else 1

    if cmd == "batch":
        result = batch_process_folder(
            args.folder,
            glob_pattern=args.glob_pattern,
            operation=args.op,
            output_dir=args.output_dir,
            language=args.lang,
            text=args.text,
            rotate=args.rotate,
            opacity=args.opacity,
            angle=args.angle,
            pages=args.pages,
            header=args.header,
            footer=args.footer,
            margin=args.margin,
            fontsize=args.fontsize,
        )
        return 0 if result.all_succeeded else 1

    logger.error("Unknown command")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
