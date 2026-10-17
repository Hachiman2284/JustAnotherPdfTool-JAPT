from __future__ import annotations

import builtins
import os
import stat
import sys
from pathlib import Path

import pytest

# pdfsuite lives in ../src, which is not on sys.path for `python tests/...` or pytest.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pdfsuite  # noqa: E402


def _feed(monkeypatch, target: object, name: str, answers: list[str]) -> list[str]:
    """Make target.name() return answers in order (EOFError when they run out).

    Returns the list of prompts it was called with.
    """
    it = iter(answers)
    prompts: list[str] = []

    def fake(prompt: str = "") -> str:
        prompts.append(prompt)
        try:
            return next(it)
        except StopIteration:
            raise EOFError from None

    monkeypatch.setattr(target, name, fake)
    return prompts


def _touch_exe(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _make_pdf(path: Path) -> Path:
    pymupdf = pytest.importorskip("pymupdf")
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "hello")
    doc.save(str(path))
    return path


# --- finding programs -------------------------------------------------------


@pytest.fixture
def fake_windows(monkeypatch, tmp_path):
    """Pretend to be on Windows with empty install folders and nothing on PATH."""
    for var in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)", "LOCALAPPDATA"):
        monkeypatch.delenv(var, raising=False)
    pf, pf86, local = tmp_path / "pf", tmp_path / "pf86", tmp_path / "local"
    monkeypatch.setenv("ProgramFiles", str(pf))
    monkeypatch.setenv("ProgramFiles(x86)", str(pf86))
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    monkeypatch.setattr(pdfsuite, "_IS_WINDOWS", True)
    monkeypatch.setattr(pdfsuite.shutil, "which", lambda name: None)
    return pf, pf86, local


def test_find_program_uses_path_first(monkeypatch, tmp_path) -> None:
    # Windows only runs files with a program extension such as .exe.
    exe = _touch_exe(tmp_path / "bin" / ("tesseract.exe" if os.name == "nt" else "tesseract"))
    monkeypatch.setenv("PATH", str(exe.parent))
    found = pdfsuite._find_tesseract()
    # Compare as files: Windows may report the extension as ".EXE".
    assert found is not None and os.path.samefile(found, exe)


def test_find_program_off_windows_ignores_install_folders(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    monkeypatch.setenv("ProgramFiles", str(tmp_path))
    _touch_exe(tmp_path / "Tesseract-OCR" / "tesseract.exe")
    monkeypatch.setattr(pdfsuite, "_IS_WINDOWS", False)
    assert pdfsuite._find_tesseract() is None


def test_find_ghostscript_picks_newest_version(fake_windows) -> None:
    pf, _, _ = fake_windows
    _touch_exe(pf / "gs" / "gs9.56.1" / "bin" / "gswin64c.exe")
    newest = _touch_exe(pf / "gs" / "gs10.04.0" / "bin" / "gswin64c.exe")
    assert pdfsuite._find_ghostscript() == str(newest)


def test_find_ghostscript_32bit_install(fake_windows) -> None:
    _, pf86, _ = fake_windows
    gs32 = _touch_exe(pf86 / "gs" / "gs10.04.0" / "bin" / "gswin32c.exe")
    assert pdfsuite._find_ghostscript() == str(gs32)


def test_find_tesseract_per_user_install(fake_windows) -> None:
    _, _, local = fake_windows
    tess = _touch_exe(local / "Programs" / "Tesseract-OCR" / "tesseract.exe")
    assert pdfsuite._find_tesseract() == str(tess)


def test_find_soffice_in_program_files(fake_windows) -> None:
    pf, _, _ = fake_windows
    soffice = _touch_exe(pf / "LibreOffice" / "program" / "soffice.exe")
    assert pdfsuite._find_soffice() == str(soffice)


def test_find_program_nothing_installed(fake_windows) -> None:
    assert pdfsuite._find_ghostscript() is None
    assert pdfsuite._find_tesseract() is None
    assert pdfsuite._find_soffice() is None


# --- setup check ------------------------------------------------------------


def _patch_tools(monkeypatch, *, tesseract=None, gs=None, soffice=None, word=None, missing=()) -> None:
    import importlib.util

    monkeypatch.setattr(pdfsuite, "_find_tesseract", lambda: tesseract)
    monkeypatch.setattr(pdfsuite, "_find_ghostscript", lambda: gs)
    monkeypatch.setattr(pdfsuite, "_find_soffice", lambda: soffice)
    monkeypatch.setattr(pdfsuite, "_word_installed", lambda: word)
    monkeypatch.setattr(importlib.util, "find_spec", lambda name, *a: None if name in missing else object())


def test_check_setup_all_ready(monkeypatch, capsys) -> None:
    _patch_tools(monkeypatch, tesseract="/t", gs="/g", soffice="/s", word=True)
    assert pdfsuite.check_setup() == 0
    out = capsys.readouterr().out
    assert "WARN" not in out and "FAIL" not in out
    assert "Microsoft Word" in out and "LibreOffice (/s)" in out


def test_check_setup_missing_programs_only_warn(monkeypatch, capsys) -> None:
    _patch_tools(monkeypatch)
    assert pdfsuite.check_setup() == 0
    out = capsys.readouterr().out
    assert out.count("[WARN]") == 3
    assert "Tesseract OCR not found" in out
    assert "Ghostscript not found" in out
    assert "neither was found" in out


def test_check_setup_word_needs_docx2pdf(monkeypatch, capsys) -> None:
    _patch_tools(monkeypatch, tesseract="/t", gs="/g", word=True, missing=("docx2pdf",))
    assert pdfsuite.check_setup() == 0
    assert "neither was found" in capsys.readouterr().out


def test_check_setup_missing_package_fails(monkeypatch, capsys) -> None:
    _patch_tools(monkeypatch, tesseract="/t", gs="/g", soffice="/s", missing=("pdf2docx",))
    assert pdfsuite.check_setup() == 1
    assert "[FAIL] Missing Python packages: pdf2docx" in capsys.readouterr().out


def test_cli_and_menu_run_check(monkeypatch) -> None:
    _patch_tools(monkeypatch, tesseract="/t", gs="/g", soffice="/s")
    assert pdfsuite.main(["check"]) == 0
    _feed(monkeypatch, builtins, "input", ["23", "", "0"])
    assert pdfsuite.interactive_menu() == 0


# --- passwords --------------------------------------------------------------


def test_prompt_password_new_rejects_empty_and_mismatch(monkeypatch) -> None:
    prompts = _feed(monkeypatch, pdfsuite.getpass, "getpass", ["", "abc", "abd", "s3cret", "s3cret"])
    assert pdfsuite._prompt_password(new=True) == "s3cret"
    assert len(prompts) == 5


def test_prompt_password_existing_asks_once(monkeypatch) -> None:
    prompts = _feed(monkeypatch, pdfsuite.getpass, "getpass", ["s3cret"])
    assert pdfsuite._prompt_password() == "s3cret"
    assert len(prompts) == 1


def test_cli_encrypt_decrypt_prompt_when_password_omitted(monkeypatch, tmp_path) -> None:
    src = _make_pdf(tmp_path / "in.pdf")
    enc, dec = tmp_path / "enc.pdf", tmp_path / "dec.pdf"

    _feed(monkeypatch, pdfsuite.getpass, "getpass", ["s3cret", "s3cret"])
    assert pdfsuite.main(["encrypt", "--in", str(src), "--out", str(enc)]) == 0
    assert pdfsuite.pdf_is_encrypted(enc) is True

    _feed(monkeypatch, pdfsuite.getpass, "getpass", ["wrong"])
    assert pdfsuite.main(["decrypt", "--in", str(enc), "--out", str(dec)]) == 1
    assert not dec.exists()

    _feed(monkeypatch, pdfsuite.getpass, "getpass", ["s3cret"])
    assert pdfsuite.main(["decrypt", "--in", str(enc), "--out", str(dec)]) == 0
    assert pdfsuite.pdf_is_encrypted(dec) is False


def test_cli_password_flag_still_works(monkeypatch, tmp_path) -> None:
    src = _make_pdf(tmp_path / "in.pdf")
    enc = tmp_path / "enc.pdf"
    prompts = _feed(monkeypatch, pdfsuite.getpass, "getpass", [])
    assert pdfsuite.main(["encrypt", "--in", str(src), "--out", str(enc), "--password", "s3cret"]) == 0
    assert prompts == []
    assert pdfsuite.decrypt_pdf(enc, tmp_path / "dec.pdf", "s3cret") is not None


def test_cli_encrypt_cancelled(monkeypatch, tmp_path) -> None:
    src = _make_pdf(tmp_path / "in.pdf")
    enc = tmp_path / "enc.pdf"

    def interrupt(prompt: str = "") -> str:
        raise KeyboardInterrupt

    monkeypatch.setattr(pdfsuite.getpass, "getpass", interrupt)
    assert pdfsuite.main(["encrypt", "--in", str(src), "--out", str(enc)]) == 1
    assert not enc.exists()


def test_menu_passwords_never_go_through_visible_input(monkeypatch, tmp_path) -> None:
    src = _make_pdf(tmp_path / "in.pdf")
    enc, dec = tmp_path / "enc.pdf", tmp_path / "dec.pdf"
    visible = _feed(monkeypatch, builtins, "input", ["8", str(src), str(enc), "", "9", str(enc), str(dec), "", "0"])
    _feed(monkeypatch, pdfsuite.getpass, "getpass", ["s3cret", "s3cret", "s3cret"])

    assert pdfsuite.interactive_menu() == 0
    assert pdfsuite.pdf_is_encrypted(enc) is True
    assert pdfsuite.pdf_is_encrypted(dec) is False
    assert not any("assword" in p for p in visible)


# --- DOCX -> PDF backend choice ---------------------------------------------


@pytest.mark.parametrize("word", [True, False])
def test_docx_to_pdf_uses_word_only_when_installed(monkeypatch, tmp_path, word) -> None:
    import types

    calls: list[tuple[str, str]] = []

    def fake_convert(src: str, out: str) -> None:
        calls.append((src, out))
        Path(out).write_bytes(b"%PDF-1.4")

    monkeypatch.setitem(sys.modules, "docx2pdf", types.SimpleNamespace(convert=fake_convert))
    monkeypatch.setattr(pdfsuite.sys, "platform", "win32")
    monkeypatch.setattr(pdfsuite, "_word_installed", lambda: word)
    monkeypatch.setattr(pdfsuite, "_find_soffice", lambda: None)

    src = tmp_path / "in.docx"
    src.write_bytes(b"")
    ok = pdfsuite.docx_to_pdf(src, tmp_path / "out.pdf")

    assert ok is word
    assert len(calls) == (1 if word else 0)
